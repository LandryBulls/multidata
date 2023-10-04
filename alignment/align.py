#!/usr/bin/env python
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_audio
import sounddevice as sd
from pydub import AudioSegment
from moviepy.editor import VideoFileClip
import numpy as np
from pathlib import Path
import librosa
from scipy.signal import correlate, resample
import librosa
import os
from tqdm import tqdm
from IPython.display import Audio, Video
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import subprocess
import time
from glob import glob

"""
This file contains functions for aligning audio and video files.

It works by extracting the audio from each video file, mixing the audio from all the microphones, and then cross-correlating
the audio from each camera with the mixed microphone audio. The time shift that maximizes the correlation is then applied
to the video files.

Once the video files are aligned, they are trimmed to the shortest duration (that is, the duration of the shortest video
determines the duration of all the videos). The microphone audio is also trimmed to the shortest duration.
"""

def extract_audio(posix_video_path):
    print("Extracting audio from video files...\n")
    out_audio_path = str(os.path.basename(str(posix_video_path)[:-4]+'.wav'))
    ffmpeg_extract_audio(str(posix_video_path), out_audio_path)
    # librosa returns the numpy array as well as the sample rate
    loaded = librosa.load(out_audio_path, sr=None)
    # delete the file
    os.remove(out_audio_path)
    # returns both the audio as a numpy array and the sample rate
    return loaded

def mix_audio(list_of_arrays):
    """
    Takes a list of numpy arrays and mixes them together, padding the shorter arrays with zeros.
    """
    # find the longest array
    max_len = max([len(arr) for arr in list_of_arrays])
    # pad the shorter arrays with zeros
    padded_arrays = [np.pad(arr, (0, max_len-len(arr)), 'constant') for arr in list_of_arrays]
    # sum the arrays
    return np.sum(padded_arrays, axis=0)

def get_shift_values(list_of_camera_audio_arrays, microphone_mix):
    """
    Takes a list of numpy arrays representing audio from each camera and a numpy array representing the microphone mix.
    Returns a list of numpy arrays representing the aligned audio from each camera.
    """
    # cross-correlate each audio stream with the mix
    # the output array represents how similar the two signals are at each time step
    all_arrays = list_of_camera_audio_arrays + [microphone_mix]

    # find the longest array
    max_pos = np.argmax(np.array([len(arr) for arr in all_arrays]))
    maxlen = len(all_arrays[max_pos])
    del all_arrays

    # pad the shorter arrays with zeros    
    list_of_camera_audio_arrays = [np.pad(arr, (0, maxlen-len(arr)), 'constant') for arr in list_of_camera_audio_arrays]
    microphone_mix = np.pad(microphone_mix, (0, maxlen-len(microphone_mix)), 'constant')

    # cross-correlate each array with the microphone mix
    print("Cross-correlating audio streams with microphone mix...\n")
    correlations = [correlate(arr, microphone_mix, mode='full') for arr in list_of_camera_audio_arrays]

    # find the time shift (in seconds) that maximizes the correlation
    print("Finding time shift that maximizes correlation...\n")
    shifts = [np.argmax(corr) - len(arr) for corr, arr in zip(correlations, list_of_camera_audio_arrays)]
    for s, shift in enumerate(shifts):
        print(f'Shift {s}: {shift} samples')
    return shifts

def trim_video(posix_video_path, start_time, end_time, output_path):
    """
    Takes a posix path to a video file, a start trim value (in seconds), an end trim value (in seconds), and an output path.
    Trims the video and saves it to the output path.
    """
    stringPath = str(posix_video_path)
    duration = VideoFileClip(stringPath).duration
    ffmpeg_command = f'ffmpeg -i {stringPath} -ss {start_time} -to {end_time} -c copy {output_path}'
    subprocess.run(ffmpeg_command, shell=True)

def trim_audio(posix_audio_path, start_time, end_time, output_path):
    """
    Takes a posix path to an audio file, a start trim value (in seconds), an end trim value (in seconds), and an output path.
    Trims the audio and saves it to the output path.
    """
    stringPath = str(posix_audio_path)
    duration = librosa.get_duration(filename=stringPath)
    ffmpeg_command = f'ffmpeg -i {stringPath} -ss {start_time} -to {end_time} -c copy {output_path}'
    subprocess.run(ffmpeg_command, shell=True)

def align_data(data_dir):
    """
    Takes a data directory containing video files and microphone audio files. Aligns the video files with the microphone audio.
    Need to add more descriptive comments for each step.
    :param data_dir:
    :type data_dir:
    :return:
    :rtype:
    """

    # data dir should already contain derivatives folder with concatenated video files and mixed microphone audio
    data_dir = Path(data_dir)
    derivative_path = data_dir / 'derivatives'
    list_of_video_paths = [str(i) for i in derivative_path.iterdir() if Path(i).suffix.lower() == '.mp4']
    # just confirm that all the video files are the concatenated ones
    list_of_video_paths = [i for i in list_of_video_paths if 'concatenated' in i]
    print(f'Found {len(list_of_video_paths)} concatenated video files')
    list_of_mic_paths = [str(i) for i in (data_dir / 'audio').iterdir()]
    print(f'Found {len(list_of_mic_paths)} microphone audio files')
    # sort the mic paths
    list_of_mic_paths.sort()

    # make mix of all mics
    print("Mixing microphone audio...\n")
    mic_mix = mix_audio([librosa.load(mic, sr=None)[0] for mic in list_of_mic_paths])
    mic_audio_sr = librosa.load(list_of_mic_paths[0], sr=None)[1]
    
    # extract audio from video files
    print("Extracting audio from video files...\n")
    video_audio = [extract_audio(vid) for vid in list_of_video_paths]
    video_audio_sr = video_audio[0][1]
    video_audio = [i[0] for i in video_audio]
    
    assert mic_audio_sr == video_audio_sr, "Sample rates of audio files do not match."
    
    # get durations of video files
    print("Getting durations of video files...\n")
    video_durations = dict(zip(list_of_video_paths, [VideoFileClip(str(vid)).duration for vid in list_of_video_paths]))
    audio_duration = mic_mix.shape[0]/mic_audio_sr
    
    # get shift values
    print("Getting shift values...\n")
    shift_values = get_shift_values(video_audio, mic_mix)
    
    # check distribution of positive and negative shifts
    if all([shift > 0 for shift in shift_values]):
        trim_status = 'early'
    elif all([shift < 0 for shift in shift_values]):
        trim_status = 'late'
    else:
        trim_status = 'mixed'
    
    start_end_keys = dict(zip(['in', 'out'], [[], []]))
    all_files = list_of_video_paths + ['audio_trim']
    trim_times = {}
    for file in all_files:
        trim_times[file] = start_end_keys.copy()
    trim_times['audio_trim'] = start_end_keys.copy()
        
    if trim_status == 'early':
        # trim the beginning of the video files
        for vid, shift in zip(list_of_video_paths, shift_values):
            trim_amount = shift/video_audio_sr
            trim_times[vid]['in'] = trim_amount
            video_durations[vid] = video_durations[vid] - trim_amount
            
        trim_times['audio_trim']['in'] = 0
        
    elif trim_status == 'late':
        # trim the end of the video files
        latest = min(shift_values)
        
        for vid, shift in zip(list_of_video_paths, shift_values):
            if shift == latest:
                trim_times[vid]['in'] = 0
            else:
                trim_amount = (abs(latest) - abs(shift))/video_audio_sr
                trim_times[vid]['in'] = trim_amount
                video_durations[vid] = video_durations[vid] - trim_amount
        
        audio_trim = abs(latest)/mic_audio_sr
        trim_times['audio_trim']['in'] = audio_trim
        audio_duration = audio_duration - audio_trim
        
    elif trim_status == 'mixed':
        latest = min(shift_values)
        for vid, shift in zip(list_of_video_paths, shift_values):
            if shift == latest:
                trim_times[vid]['in'] = 0
            elif shift > 0:
                trim_amount = (abs(shift)+abs(latest))/video_audio_sr
                trim_times[vid]['in'] = trim_amount
                video_durations[vid] = video_durations[vid] - trim_amount
            else:
                trim_amount = (abs(latest) - abs(shift))/video_audio_sr
                trim_times[vid]['in'] = trim_amount
                video_durations[vid] = video_durations[vid] - trim_amount
        
        audio_trim = abs(latest)/mic_audio_sr
        trim_times['audio_trim']['in'] = audio_trim
        audio_duration = audio_duration - audio_trim
    
    # get ending trim times
    all_durations = list(video_durations.values()) + [audio_duration]    
    shortest = min(all_durations)
    for file in trim_times.keys():
        trim_times[file]['out'] = shortest + trim_times[file]['in']

    derivative_path = data_dir / 'derivatives'
        
    # trim the video files
    print("Trimming video files...\n")
    # all the trim times are in seconds
    for vid in list_of_video_paths:
        trim_video(vid, trim_times[vid]['in'], trim_times[vid]['out'], str(derivative_path / f'{os.path.basename(str(vid))[:-4]}_trimmed.mp4'))
        
    # trim the audio files
    print("Trimming audio files...\n")
    for mic in list_of_mic_paths:
        trim_audio(mic, trim_times['audio_trim']['in'], trim_times['audio_trim']['out'], str(derivative_path / f'{os.path.basename(str(mic))[:-4]}_trimmed.wav'))
