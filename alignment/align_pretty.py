import numpy as np
import librosa
from scipy.signal import correlate
from pathlib import Path
import subprocess
from moviepy.editor import VideoFileClip

def extract_audio(video_path):
    audio, sr = librosa.load(str(video_path), sr=None)
    return audio, sr

def mix_audio(audio_list):
    max_len = max(len(audio) for audio in audio_list)
    return np.sum([np.pad(audio, (0, max_len - len(audio)), 'constant') for audio in audio_list], axis=0)

def get_shift_values(camera_audios, mic_mix):
    max_len = max(len(audio) for audio in camera_audios + [mic_mix])
    padded_audios = [np.pad(audio, (0, max_len - len(audio)), 'constant') for audio in camera_audios]
    padded_mic_mix = np.pad(mic_mix, (0, max_len - len(mic_mix)), 'constant')
    
    correlations = [correlate(audio, padded_mic_mix, mode='full') for audio in padded_audios]
    return [np.argmax(corr) - len(audio) for corr, audio in zip(correlations, padded_audios)]

def trim_media(input_path, start_time, end_time, output_path):
    cmd = f'ffmpeg -i {input_path} -ss {start_time} -to {end_time} -c copy {output_path}'
    subprocess.run(cmd, shell=True, check=True)

def align_data(data_dir):
    data_dir = Path(data_dir)
    derivative_path = data_dir / 'derivatives'
    video_paths = list(derivative_path.glob('*concatenated*.mp4'))
    mic_paths = sorted(list((data_dir / 'audio').glob('*.wav')))

    print(f"Found {len(video_paths)} video files and {len(mic_paths)} audio files")

    mic_mix = mix_audio([librosa.load(str(mic), sr=None)[0] for mic in mic_paths])
    video_audios = [extract_audio(video)[0] for video in video_paths]
    
    shift_values = get_shift_values(video_audios, mic_mix)
    video_durations = [VideoFileClip(str(video)).duration for video in video_paths]
    audio_duration = len(mic_mix) / librosa.get_samplerate(str(mic_paths[0]))

    trim_times = {}
    if all(shift > 0 for shift in shift_values):
        for video, shift in zip(video_paths, shift_values):
            trim_times[video] = {'in': shift / librosa.get_samplerate(str(video)), 'out': min(video_durations)}
        trim_times['audio'] = {'in': 0, 'out': min(video_durations)}
    elif all(shift < 0 for shift in shift_values):
        latest = min(shift_values)
        for video, shift in zip(video_paths, shift_values):
            trim_times[video] = {'in': (abs(latest) - abs(shift)) / librosa.get_samplerate(str(video)), 'out': min(video_durations)}
        trim_times['audio'] = {'in': abs(latest) / librosa.get_samplerate(str(mic_paths[0])), 'out': min(video_durations)}
    else:
        latest = min(shift_values)
        for video, shift in zip(video_paths, shift_values):
            if shift > 0:
                trim_times[video] = {'in': (abs(shift) + abs(latest)) / librosa.get_samplerate(str(video)), 'out': min(video_durations)}
            else:
                trim_times[video] = {'in': (abs(latest) - abs(shift)) / librosa.get_samplerate(str(video)), 'out': min(video_durations)}
        trim_times['audio'] = {'in': abs(latest) / librosa.get_samplerate(str(mic_paths[0])), 'out': min(video_durations)}

    for video in video_paths:
        trim_media(video, trim_times[video]['in'], trim_times[video]['out'], 
                   derivative_path / f"{video.stem}_trimmed{video.suffix}")

    for mic in mic_paths:
        trim_media(mic, trim_times['audio']['in'], trim_times['audio']['out'], 
                   derivative_path / f"{mic.stem}_trimmed{mic.suffix}")

    print("Trim times:")
    for file, times in trim_times.items():
        print(f"{file}: {times['in']}s to {times['out']}s")

    return list(derivative_path.glob('*trimmed*'))

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        align_data(sys.argv[1])
    else:
        print("Please provide the data directory as an argument.")