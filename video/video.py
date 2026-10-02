import os
import shutil
import tempfile
from pathlib import Path
import subprocess

"""
This file contains functions for concatenating video files and converting 360 footage to equirectangular projection.
"""

def make_derivative_folder(data_dir):
    data_dir = Path(data_dir)
    derivative_path = data_dir / 'derivatives'
    os.makedirs(str(derivative_path), exist_ok=True)
    return derivative_path

_ANNEXB = {'hevc': ('hevc_mp4toannexb', 'hev1'), 'h264': ('h264_mp4toannexb', 'avc3')}


def _probe_v(path, entries):
    return subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', entries,
                           '-show_data', '-of', 'default', str(path)],
                          capture_output=True, text=True, check=True).stdout


def concat_stream_copy(chapters, out_path, list_path, scratch_dir=None):
    """Stream-copy concat of camera chapter files listed (in order) in `list_path`.

    A plain concat demuxer + `-c copy` keeps the FIRST chapter's sample description
    (hvcC/avcC: VPS/SPS/PPS) for the whole output. Chapters exported in different
    passes (2025-11-16_000: GS010172 exported 2026-04-06, level 6.1 with 4 temporal
    sub-layers; GS02-04 exported 2026-04-10, level 6.2 with 1) carry different
    parameter sets, so every later chapter decodes against the wrong SPS
    ("No ref lists in the SPS", picture frozen between keyframes).

    When the chapters' parameter sets differ, each chapter is first remuxed with
    `*_mp4toannexb`, which writes that chapter's own parameter sets in-band at every
    IRAP (tag hev1/avc3), and the concat list pins each file's duration to the
    source chapter's, so video/audio timestamps and the audio holes at the joins are
    identical to a plain concat. No re-encode either way.
    """
    chapters = [Path(c) for c in chapters]
    tmp = None
    if len({_probe_v(c, 'stream=extradata') for c in chapters}) > 1:
        codec = _probe_v(chapters[0], 'stream=codec_name').split('codec_name=')[1].split()[0]
        if codec not in _ANNEXB:
            raise RuntimeError(f'chapters for {out_path} have different {codec} parameter sets; '
                               'a plain stream-copy concat would be undecodable after chapter 1')
        bsf, tag = _ANNEXB[codec]
        print(f'Chapters have different {codec} parameter sets; writing them in-band before concat')
        base = scratch_dir or os.environ.get('MULTIDATA_SCRATCH') or '/fastscratch/pipeline_scratch'
        tmp = Path(tempfile.mkdtemp(prefix='concat_inband_',
                                    dir=base if os.path.isdir(base) else Path(out_path).parent))
        lines = ['ffconcat version 1.0']
        for c in chapters:
            dur = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                  '-of', 'csv=p=0', str(c)],
                                 capture_output=True, text=True, check=True).stdout.strip()
            inband = tmp / c.name
            subprocess.run(['ffmpeg', '-y', '-v', 'warning', '-i', str(c), '-map', '0:v', '-map', '0:a:0',
                            '-c', 'copy', '-bsf:v', bsf, '-tag:v', tag, str(inband)], check=True)
            lines += [f"file '{inband}'", f'duration {dur}']
        list_path = tmp / 'concat_list.txt'
        list_path.write_text('\n'.join(lines) + '\n')
    try:
        subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(list_path),
                        '-map', '0:v', '-map', '0:a:0', '-c', 'copy', str(out_path)], check=True)
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)


def concatenate(cam_directory, dest_directory):
    dest_directory = Path(dest_directory)
    cam_identity = os.path.basename(cam_directory)
    camera_path = Path(cam_directory)
    print(camera_path)

    to_concat = [i for i in camera_path.iterdir() if Path(i).suffix.lower() == '.mp4' and not '_' in str(i.name)]

    if len(to_concat) == 0:
        print(f"No .mp4 files found in {cam_identity}")
        return None

    to_concat.sort()

    add_text = dest_directory / f'{cam_identity}_concat_history.txt'

    with open(str(add_text), "w") as f:
        for v in to_concat:
            f.write('file ' + str(v) + "\n")

    # just put the .mp4's in the same directory, then put the trimmed files in derivatives later
    filename = f'{cam_identity}_concatenated.mp4'
    filepath = dest_directory / filename
    # check if filename exists, is non-trivial size, and is a valid video (moov atom present)
    if filepath.exists() and filepath.stat().st_size > 1000:
        probe = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
             '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', str(filepath)],
            capture_output=True, text=True,
        )
        if probe.returncode == 0 and 'video' in probe.stdout:
            print(f"{filename} already exists in {dest_directory}. Skipping concatenation.")
            return filename
        else:
            print(f"{filename} exists but is corrupt (ffprobe failed). Re-concatenating...")
            filepath.unlink()

    print(f"Concatenating {cam_identity}...")
    concat_stream_copy(to_concat, dest_directory / filename, add_text)
    return filename


def apply_concatenation(data_dir):
    data_dir = Path(data_dir)
    derivative_path = make_derivative_folder(data_dir)
    # get all camera directories (use i.name to avoid matching on parent path components)
    cam_directories = [i for i in Path(data_dir).iterdir() if ('cam' in i.name or '360' in i.name) and i.is_dir()]
    concat_files = []
    for cam in cam_directories:
        concat_file = concatenate(cam, derivative_path)
        concat_files.append(concat_file)

    # returns a list of filenames of the concatenated videos
    return concat_files

def concatenate_360(data_dir):
    data_dir = Path(data_dir)
    derivative_path = make_derivative_folder(data_dir)
    # get the 360 camera directory
    cam_directory = [i for i in Path(data_dir).iterdir() if '360' in str(i)][0]
    concat_files = concatenate(cam_directory, derivative_path)
    # returns a list of filenames of the concatenated videos
    return concat_files
