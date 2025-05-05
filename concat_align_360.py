#!/usr/bin/env python



### USE CONDA ENVIRONMENT: annotate ###

"""
This script processes and aligns 360-degree camera videos with regular camera footage using audio synchronization.

The script performs two main functions:
1. Concatenates multiple 360-degree video files from a session into a single video file
2. Aligns the concatenated 360 video with existing camera footage using audio cross-correlation

The alignment process:
- Extracts audio from both the 360 video and a reference camera video
- Uses cross-correlation to find the optimal alignment point between the two audio streams
- Trims the 360 video to match the timing of the reference video
- Outputs the aligned video as '*_concatenated_trimmed.mp4'

Usage:
    The script reads the data directory path from 'data_management/main_data_dir.txt'
    and processes all sessions containing 360-degree camera footage.

Requirements:
    - ffmpeg: for video concatenation and trimming
    - librosa: for audio processing
    - scipy: for cross-correlation calculations
    - numpy: for numerical operations
    - tqdm: for progress tracking
"""

from pathlib import Path
import subprocess
import librosa
import numpy as np
from scipy import signal
from tqdm import tqdm

def align_360(session_dir):
    """Align the 360 video with existing camera videos using audio cross-correlation"""
    derivatives_dir = session_dir / 'derivatives'
    
    # Use first aligned camera video as reference
    ref_video = next(derivatives_dir.glob('cam*_concatenated_trimmed.mp4'))
    
    # Check if 360 concatenated video exists
    concat_file = derivatives_dir / '360cam_concatenated.mp4'
    if not concat_file.exists():
        return

    # Extract audio from videos for comparison
    def extract_audio(video_path):
        """Extract audio from video file and return the waveform and sample rate"""
        y, sr = librosa.load(video_path)
        return y, sr

    print("Extracting audio from videos...")
    y_360, sr_360 = extract_audio(concat_file)
    y_ref, sr_ref = extract_audio(ref_video)

    # Compute cross-correlation
    correlation = signal.correlate(y_360, y_ref, mode='full')
    lags = signal.correlation_lags(len(y_360), len(y_ref))
    lag_time = lags / sr_360  # Convert to seconds

    # Find the peak correlation
    max_corr_idx = np.argmax(np.abs(correlation))
    offset_seconds = lag_time[max_corr_idx]

    print(f"Estimated offset: {offset_seconds:.3f} seconds")

    # Calculate trim points
    if offset_seconds > 0:
        # 360 video starts BEFORE reference (need to trim 360)
        trim_start = offset_seconds
    else:
        # 360 video starts AFTER reference (no need to trim start)
        trim_start = 0

    # Calculate duration and end point based on shortest video after alignment
    dur_360 = len(y_360) / sr_360
    dur_ref = len(y_ref) / sr_ref
    
    if offset_seconds > 0:
        trim_duration = min(dur_360 - trim_start, dur_ref)
    else:
        trim_duration = min(dur_360, dur_ref + offset_seconds)

    # Create the trimmed version using ffmpeg
    output_file = derivatives_dir / '360cam_concatenated_trimmed.mp4'
    
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-i', str(concat_file),
        '-ss', str(trim_start),
        '-t', str(trim_duration),
        '-c', 'copy',
        str(output_file)
    ]
    
    subprocess.run(ffmpeg_cmd, check=True)

def process_360_videos(data_dir, overwrite=False):
    """Process and align 360 videos with existing camera videos"""
    data_dir = Path(data_dir)
    
    # Find sessions to process
    session_dirs = [d for d in data_dir.iterdir() if d.is_dir()]
    session_dirs = [d for d in session_dirs 
                   if (d / 'derivatives').exists() 
                   and any('360' in x.name for x in d.iterdir())
                   and (overwrite or not (d / 'derivatives' / '360cam_concatenated_trimmed.mp4').exists())]
    
    print(f"\nFound {len(session_dirs)} sessions to process:")
    for session in session_dirs:
        print(f"  - {session.name}")
    ok = input("\nContinue? (y/n): ")
    if ok.lower() != 'y':
        return
    
    for session_dir in tqdm(session_dirs):
        print(f"\nProcessing {session_dir}...")
        try:
            derivatives_dir = session_dir / 'derivatives'
            cam_360_dir = next(d for d in session_dir.iterdir() if '360' in d.name)
            
            # Concatenate 360 videos first
            video_files = sorted([f for f in cam_360_dir.iterdir() 
                                if f.suffix.lower() == '.mp4' and not f.name.startswith('.')])
            if not video_files:
                print(f"Skipping {session_dir}: No 360 videos found")
                continue
            
            # Concatenate 360 videos
            concat_file = derivatives_dir / '360cam_concatenated.mp4'
            history_file = derivatives_dir / '360cam_concat_history.txt'
            if not concat_file.exists() or overwrite:
                print(f"Concatenating {len(video_files)} 360 videos in {session_dir.name}")
                with open(history_file, 'w') as f:
                    for video in video_files:
                        f.write(f"file '{video}'\n")
                subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', 
                            '-i', str(history_file), '-c', 'copy', str(concat_file)], check=True)
            
            # Align 360 video
            align_360(session_dir)
            
        except Exception as e:
            print(f"Error processing {session_dir}: {e}")
            continue

if __name__ == "__main__":
    with open('data_management/main_data_dir.txt', 'r') as f:
        data_dir = Path(f.read().strip())
    process_360_videos(data_dir, overwrite=False)
