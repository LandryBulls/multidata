#!/usr/bin/env python
"""
Align each session's camera videos and microphone tracks, and trim them to a
common, frame-exact start.

    derivatives/{cam}_concatenated.mp4  +  audio/TRACK0N.WAV
        -> derivatives/{cam}_concatenated_trimmed.mp4
           derivatives/TRACK0N_trimmed.wav
           derivatives/trim_alignment.json      (every number used, and the checks)

1. Estimate. Each camera's onboard audio is matched to the mix of the mics on
   log-RMS envelopes (250 Hz): a whole-session cross-correlation gives a coarse
   lag, then 30 s windows across the session are refined around it, and a
   robust line  lag(t) = offset + drift * t  is fitted per camera. Envelopes are
   used rather than raw waveforms because a far-field camera mic and close-talk
   lavs differ in spectrum and reverberation but agree on when sound happens.
   A fit that does not lock (too few windows, large residuals, absurd drift)
   raises rather than trimming on a guess.

2. Clock drift. The cameras run ~0.2 s/hour fast against the Zoom recorder. The
   mic tracks are resampled (soxr, ~60 ppm) onto the median camera clock, so a
   second of mic audio is a second of video for the whole session. What remains
   is camera-to-camera drift, reported in the JSON.

3. Trim. Video is re-encoded (hevc_nvenc) from the exact frame nearest each
   camera's in-point, and every camera gets the same frame count. The earlier
   `-ss ... -c copy` could only start on a keyframe (every 0.5-1.0 s), so frame
   0 landed up to a GOP after the in-point -- 0.37 s on 2024-05-22_000 cam1.
   Mic tracks are cut sample-exactly in numpy.

4. Verify. Each output is ffprobed (streams start at 0, frame count), and its
   own audio is re-matched against the trimmed mics: the residual lag must be
   ~0 across the whole session.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf
import soxr
from scipy.signal import correlate, correlation_lags

ANALYSIS_SR = 16000          # decode rate for estimation
ENV_HOP = 64                 # -> 250 Hz envelope, 4 ms per step
ENV_HZ = ANALYSIS_SR / ENV_HOP
WINDOW_S = 30.0
STEP_S = 30.0
SEARCH_S = 1.0               # refinement search around the coarse lag
MIN_WINDOW_R = 0.3           # a window counts only if its envelopes correlate this well
MIN_WINDOWS = 8
MIN_ACCEPTED_FRACTION = 0.5
MAX_RESIDUAL_S = 0.015       # RMS of the fit residual
MAX_ABS_DRIFT = 2e-4         # 0.72 s/hour; measured values are ~6e-5
VERIFY_MAX_LAG_S = 0.020     # trimmed outputs: |residual lag| everywhere below this

CAMERAS = ['cam1', 'cam2', '360cam']
ENCODER = 'hevc_nvenc'
ENCODE_ARGS = ['-preset', 'p5', '-tune', 'hq', '-rc', 'vbr', '-cq', '18', '-b:v', '0']
AUDIO_ARGS = ['-c:a', 'aac', '-b:a', '192k']


class AlignmentError(RuntimeError):
    """The estimate or the result failed its confidence checks."""


# ----------------------------------------------------------------------- tools

def find_ffmpeg(encoder=ENCODER):
    """An ffmpeg that can encode with `encoder` ($FFMPEG_BIN first)."""
    candidates = [os.environ.get('FFMPEG_BIN'), '/usr/bin/ffmpeg', shutil.which('ffmpeg'),
                  '/snap/bin/ffmpeg']
    for c in candidates:
        if not c or not Path(c).exists():
            continue
        r = subprocess.run([c, '-hide_banner', '-encoders'], capture_output=True, text=True)
        if encoder in r.stdout:
            return c
    raise AlignmentError(f'no ffmpeg with {encoder} found (tried {[c for c in candidates if c]}); '
                         f'set FFMPEG_BIN')


def probe(path):
    """First video and first audio stream: start, duration, fps, frame count."""
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                        'stream=codec_type,start_time,r_frame_rate,nb_frames,duration',
                        '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    out = {}
    for st in json.loads(r.stdout)['streams']:
        kind = st['codec_type']
        if kind in out:
            continue
        num, den = (st.get('r_frame_rate') or '0/1').split('/')
        nb = st.get('nb_frames')
        out[kind] = dict(start=float(st.get('start_time') or 0.0),
                         duration=float(st.get('duration') or 0.0),
                         fps=float(num) / float(den) if float(den) else 0.0,
                         frames=int(nb) if nb not in (None, 'N/A') else None)
    return out


def decode_mono(path, sr=ANALYSIS_SR):
    """Whole file's first audio stream, mono float32 at `sr`. Sample 0 is the
    stream's first sample, i.e. PTS = its start_time."""
    out = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0', '-ac', '1',
                          '-ar', str(sr), '-f', 's16le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(out, '<i2').astype(np.float32) / 32768.0


def envelope(x):
    n = len(x) // ENV_HOP
    e = np.log(np.sqrt((x[:n * ENV_HOP].reshape(n, ENV_HOP) ** 2).mean(1)) + 1e-5)
    return ((e - e.mean()) / (e.std() + 1e-9)).astype(np.float32)


def _peak(c, k):
    """Parabolic sub-sample refinement of a correlation peak at index k."""
    if 0 < k < len(c) - 1:
        a, b, d = c[k - 1], c[k], c[k + 1]
        den = a - 2 * b + d
        if den < 0:
            return k + 0.5 * (a - d) / den
    return float(k)


# ------------------------------------------------------------------ estimation

def coarse_lag(cam_env, mic_env):
    """Camera time minus mic time (s), from whole-session envelopes."""
    c = correlate(cam_env, mic_env, mode='full', method='fft')
    lags = correlation_lags(len(cam_env), len(mic_env), mode='full')
    return lags[int(np.argmax(c))] / ENV_HZ


def windowed_lags(cam_env, mic_env, coarse):
    """(mic_t_centre, lag, r) per window, lag = camera time - mic time."""
    win, search = int(WINDOW_S * ENV_HZ), int(SEARCH_S * ENV_HZ)
    rows = []
    t0 = 0.0
    while True:
        m0 = int(round(t0 * ENV_HZ))
        c0 = int(round((t0 + coarse) * ENV_HZ)) - search
        if m0 + win > len(mic_env):
            break
        if c0 >= 0 and c0 + win + 2 * search <= len(cam_env):
            ref = mic_env[m0:m0 + win].astype(np.float64)
            ref = (ref - ref.mean()) / (ref.std() + 1e-9)
            seg = cam_env[c0:c0 + win + 2 * search].astype(np.float64)
            c = np.correlate(seg, ref, mode='valid')
            # Pearson r: ref is zero-mean, so only the segment's local std is needed
            csum = np.concatenate([[0.0], np.cumsum(seg)])
            csq = np.concatenate([[0.0], np.cumsum(seg ** 2)])
            mu = (csum[win:] - csum[:-win]) / win
            sd = np.sqrt(np.maximum((csq[win:] - csq[:-win]) / win - mu ** 2, 1e-12))
            r = c / (win * sd)
            k = int(np.argmax(r))
            lag = (c0 + _peak(r, k)) / ENV_HZ - t0
            rows.append((t0 + WINDOW_S / 2, lag, float(r[k])))
        t0 += STEP_S
    return rows


def fit_line(rows):
    """Robust lag(t) = offset + drift * t. Returns (offset, drift, rms, used, total)."""
    good = [(t, l) for t, l, r in rows if r >= MIN_WINDOW_R]
    if len(good) < 2:
        return None, None, None, len(good), len(rows)
    t, l = np.array(good).T
    keep = np.ones(len(t), bool)
    for _ in range(3):
        drift, offset = np.polyfit(t[keep], l[keep], 1)
        res = l - (offset + drift * t)
        mad = np.median(np.abs(res[keep] - np.median(res[keep]))) * 1.4826
        new = np.abs(res) <= max(3 * mad, 0.005)
        if new.sum() < 2 or np.array_equal(new, keep):
            break
        keep = new
    drift, offset = np.polyfit(t[keep], l[keep], 1)
    rms = float(np.sqrt(np.mean((l[keep] - (offset + drift * t[keep])) ** 2)))
    return float(offset), float(drift), rms, int(keep.sum()), len(rows)


def check_fit(name, fit):
    offset, drift, rms, used, total = fit
    problems = []
    if offset is None or used < MIN_WINDOWS:
        problems.append(f'only {used} of {total} windows locked (need {MIN_WINDOWS})')
    elif used < MIN_ACCEPTED_FRACTION * total:
        problems.append(f'only {used} of {total} windows locked (need {MIN_ACCEPTED_FRACTION:.0%})')
    else:
        if rms > MAX_RESIDUAL_S:
            problems.append(f'residual {rms * 1000:.1f} ms > {MAX_RESIDUAL_S * 1000:.0f} ms')
        if abs(drift) > MAX_ABS_DRIFT:
            problems.append(f'drift {drift * 3600:+.2f} s/hour is implausible')
    if problems:
        raise AlignmentError(f'{name}: alignment did not lock -- ' + '; '.join(problems))


# ---------------------------------------------------------------------- trims

def trim_video(ffmpeg, src, dst, first_frame, n_frames, fps, v_start):
    """Re-encode frames [first_frame, first_frame + n_frames) of src into dst.

    The seek lands 1 ms before the target frame's timestamp; with input-side -ss
    and a re-encode, ffmpeg decodes from the preceding keyframe and discards
    everything earlier, so the first output frame IS `first_frame`.
    """
    ss = v_start + first_frame / fps - 0.001
    tmp = dst.with_name(f'.{dst.stem}.partial-{os.getpid()}.mp4')
    cmd = [ffmpeg, '-v', 'error', '-y', '-ss', f'{ss:.6f}', '-i', str(src),
           '-map', '0:v:0', '-map', '0:a:0', '-frames:v', str(n_frames),
           '-t', f'{n_frames / fps:.6f}', '-c:v', ENCODER, *ENCODE_ARGS, *AUDIO_ARGS, str(tmp)]
    try:
        subprocess.run(cmd, check=True)
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink()


def write_mic(src, dst, ratio, start_s, n_samples):
    """Stretch by `ratio` onto the grid clock, then cut [start_s, +n_samples)."""
    x, sr = sf.read(str(src), dtype='float32', always_2d=False)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if ratio != 1.0:
        x = soxr.resample(x, sr, sr * ratio, quality='VHQ')
    i0 = int(round(start_s * sr))
    y = x[i0:i0 + n_samples]
    if len(y) < n_samples:
        y = np.pad(y, (0, n_samples - len(y)))
    tmp = dst.with_name(f'.{dst.stem}.partial-{os.getpid()}.wav')
    sf.write(str(tmp), np.clip(y, -1.0, 1.0), sr, subtype='PCM_16')
    os.replace(tmp, dst)


# ------------------------------------------------------------------- session

def session_inputs(data_dir, cameras=CAMERAS):
    deriv = Path(data_dir) / 'derivatives'
    videos = {c: deriv / f'{c}_concatenated.mp4' for c in cameras}
    missing = [str(v) for v in videos.values() if not v.exists()]
    if missing:
        raise AlignmentError(f'missing concatenated video(s): {missing}')
    audio = Path(data_dir) / 'audio'
    mics = sorted(p for p in audio.iterdir()
                  if p.suffix.lower() == '.wav' and not p.name.startswith('.')) if audio.is_dir() else []
    if not mics:
        raise AlignmentError(f'no mic tracks in {audio}')
    return videos, mics


def expected_outputs(data_dir, cameras=CAMERAS):
    videos, mics = session_inputs(data_dir, cameras)
    deriv = Path(data_dir) / 'derivatives'
    return ([deriv / f'{c}_concatenated_trimmed.mp4' for c in videos]
            + [deriv / f'{m.stem}_trimmed.wav' for m in mics])


def align_data(data_dir, force=False, cameras=CAMERAS):
    """Align and trim one session. Returns the paths written."""
    data_dir = Path(data_dir)
    deriv = data_dir / 'derivatives'
    videos, mics = session_inputs(data_dir, cameras)
    outputs = expected_outputs(data_dir, cameras)
    if all(p.exists() for p in outputs) and not force:
        print(f'All {len(outputs)} trimmed files already exist, skipping alignment.')
        return [str(p) for p in outputs]

    ffmpeg = find_ffmpeg()
    report = dict(session=data_dir.name, created=datetime.now().isoformat(timespec='seconds'),
                  ffmpeg=ffmpeg, encoder=[ENCODER, *ENCODE_ARGS], cameras={}, mics={})

    # --- estimate -----------------------------------------------------------
    print(f'Decoding {len(mics)} mic tracks and {len(videos)} camera audio streams...')
    mic_audio = [decode_mono(m) for m in mics]
    n = max(len(a) for a in mic_audio)
    mix = sum(np.pad(a / (np.sqrt(np.mean(a ** 2)) + 1e-9), (0, n - len(a))) for a in mic_audio)
    mic_env = envelope(mix)
    mic_dur = n / ANALYSIS_SR

    info = {}
    for cam, path in videos.items():
        streams = probe(path)
        if 'video' not in streams or 'audio' not in streams:
            raise AlignmentError(f'{cam}: need a video and an audio stream in {path}')
        cam_env = envelope(decode_mono(path))
        coarse = coarse_lag(cam_env, mic_env)
        rows = windowed_lags(cam_env, mic_env, coarse)
        fit = fit_line(rows)
        offset, drift, rms, used, total = fit
        print(f'  {cam}: coarse {coarse:+.3f} s -> '
              + ('no fit' if offset is None else
                 f'offset {offset:+.4f} s, drift {drift * 3600:+.3f} s/hour, '
                 f'residual {rms * 1000:.1f} ms')
              + f', {used}/{total} windows')
        report['cameras'][cam] = dict(
            source=str(path), coarse_lag_s=coarse, offset_s=offset, drift=drift,
            drift_s_per_hour=None if drift is None else drift * 3600,
            residual_rms_s=rms, windows_used=used, windows_total=total,
            windows=[dict(t=round(t, 2), lag=round(l, 5), r=round(r, 3)) for t, l, r in rows])
        check_fit(cam, fit)
        info[cam] = dict(offset=offset, drift=drift, fps=streams['video']['fps'],
                         v_start=streams['video']['start'], a_start=streams['audio']['start'],
                         v_end=streams['video']['start'] + streams['video']['duration'])

    fps = {cam: c['fps'] for cam, c in info.items()}
    if max(fps.values()) - min(fps.values()) > 1e-3:
        raise AlignmentError(f'cameras disagree on frame rate: {fps}')
    rate = float(np.median(list(fps.values())))

    # --- common timeline ----------------------------------------------------
    # Envelope time 0 is the camera's first audio sample, i.e. PTS a_start, so
    # the camera PTS of mic instant t is  a_start + offset + (1 + drift) * t.
    # Mics are stretched by k = 1 + median drift; grid time u = k * t.
    k = 1.0 + float(np.median([c['drift'] for c in info.values()]))
    for c in info.values():
        c['at0'] = c['a_start'] + c['offset']          # camera PTS at grid u = 0
        c['rate'] = (1.0 + c['drift']) / k            # camera seconds per grid second
    start_u = max(0.0, max(-c['at0'] / c['rate'] for c in info.values()))

    first, avail = {}, {}
    for cam, c in info.items():
        in_pts = c['at0'] + c['rate'] * start_u
        first[cam] = int(round((in_pts - c['v_start']) * c['fps']))
        avail[cam] = int(np.floor((c['v_end'] - in_pts) * c['fps'])) - 1
        frame_pts = c['v_start'] + first[cam] / c['fps']
        report['cameras'][cam].update(
            fps=c['fps'], in_point_pts_s=in_pts, first_frame=first[cam],
            first_frame_pts_s=frame_pts, in_point_error_s=frame_pts - in_pts,
            clock_rate_vs_grid=c['rate'],
            end_drift_vs_grid_s=None)
    mic_frames = int(np.floor((mic_dur * k - start_u) * rate)) - 1
    n_frames = min(min(avail.values()), mic_frames)
    duration_u = n_frames / rate
    for cam, c in info.items():
        report['cameras'][cam]['end_drift_vs_grid_s'] = (c['rate'] - 1.0) * duration_u
    report.update(mic_resample_ratio=k, mic_resample_ppm=(k - 1) * 1e6, start_s_grid=start_u,
                  n_frames=n_frames, duration_s=duration_u, fps=rate)
    print(f'  mics stretched by {(k - 1) * 1e6:+.1f} ppm; common start {start_u:.3f} s; '
          f'{n_frames} frames ({duration_u:.2f} s); in-point error '
          + ', '.join(f'{cam} {report["cameras"][cam]["in_point_error_s"] * 1000:+.1f} ms' for cam in info))

    # --- trim ---------------------------------------------------------------
    deriv.mkdir(exist_ok=True)
    print(f'Trimming {len(videos)} videos ({ENCODER}) and {len(mics)} mic tracks...')
    with ThreadPoolExecutor(len(videos)) as pool:
        jobs = [pool.submit(trim_video, ffmpeg, path, deriv / f'{cam}_concatenated_trimmed.mp4',
                            first[cam], n_frames, info[cam]['fps'], info[cam]['v_start'])
                for cam, path in videos.items()]
        for m in mics:
            sr = sf.info(str(m)).samplerate
            write_mic(m, deriv / f'{m.stem}_trimmed.wav', k, start_u, int(round(duration_u * sr)))
            report['mics'][m.stem] = dict(source=str(m), sample_rate=sr)
        for j in jobs:
            j.result()

    # --- verify -------------------------------------------------------------
    print('Verifying trimmed outputs...')
    try:
        verify(data_dir, videos, mics, n_frames, rate, report)
    finally:
        (deriv / 'trim_alignment.json').write_text(json.dumps(report, indent=2))
    print(f'  wrote {deriv / "trim_alignment.json"}')
    return [str(p) for p in outputs] + [str(deriv / 'trim_alignment.json')]


def verify(data_dir, videos, mics, n_frames, fps, report):
    """Re-measure the outputs; raise if any is off."""
    deriv = Path(data_dir) / 'derivatives'
    trimmed = [decode_mono(deriv / f'{m.stem}_trimmed.wav') for m in mics]
    mic_env = envelope(sum(a / (np.sqrt(np.mean(a ** 2)) + 1e-9) for a in trimmed))
    problems = []
    for cam in videos:
        out = deriv / f'{cam}_concatenated_trimmed.mp4'
        st = probe(out)
        v, a = st.get('video', {}), st.get('audio', {})
        rows = windowed_lags(envelope(decode_mono(out)), mic_env, 0.0)
        good = [l for _, l, r in rows if r >= MIN_WINDOW_R]
        worst = max(abs(l) for l in good) if good else None
        chk = dict(frames=v.get('frames'), video_start_s=v.get('start'), audio_start_s=a.get('start'),
                   residual_lag_median_s=float(np.median(good)) if good else None,
                   residual_lag_max_abs_s=worst, windows_used=len(good), windows_total=len(rows))
        report['cameras'][cam]['verify'] = chk
        print(f'  {cam}: {chk["frames"]} frames, video/audio start {v.get("start")}/{a.get("start")} s, '
              f'residual lag median {chk["residual_lag_median_s"]:+.4f} s, max |{worst:.4f}| s '
              f'({len(good)}/{len(rows)} windows)' if good else f'  {cam}: no windows locked')
        if v.get('frames') is not None and v['frames'] != n_frames:
            problems.append(f'{cam}: {v["frames"]} frames, expected {n_frames}')
        if abs(v.get('start', 1.0)) > 0.5 / fps:
            problems.append(f'{cam}: video starts at {v.get("start")} s')
        if worst is None or worst > VERIFY_MAX_LAG_S:
            problems.append(f'{cam}: residual lag {worst} s exceeds {VERIFY_MAX_LAG_S} s')
    report['verified'] = not problems
    if problems:
        raise AlignmentError('trimmed outputs failed verification: ' + '; '.join(problems))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Align and trim one session (see module docstring).')
    ap.add_argument('session_dir')
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args()
    try:
        align_data(args.session_dir, force=args.force)
    except AlignmentError as e:
        sys.exit(f'ALIGNMENT FAILED: {e}')
