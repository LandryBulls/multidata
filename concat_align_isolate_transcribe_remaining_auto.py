#!/usr/bin/env python
# coding: utf-8

"""
This script will fully process all data from the main data directory, including concatenation, alignment, audio isolation, and transcription.
"""

from isolate_and_transcribe import extract_transcripts
from concatenate_align import process_folder
from pathlib import Path
import os
import json
from tqdm import tqdm

def save_transcript(transcript_data, output_path):
    """Save transcript data as JSON instead of PKL"""
    with open(output_path.with_suffix('.json'), 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=2)

def get_folders_needing_processing(data_dir):
    needs_concat_processing = []
    needs_audio_processing = []

    pbar = tqdm(list(data_dir.iterdir()), desc='Checking folders')
    for dir_path in data_dir.iterdir():
        pbar.update(1)
        if not dir_path.is_dir():
            continue
        audio_dir = dir_path / 'audio'
        derivatives_dir = dir_path / 'derivatives'

        if not audio_dir.is_dir():
            continue

        # Check for concatenation and alignment
        if not (derivatives_dir / 'cam1_concatenated_trimmed.mp4').exists():
            needs_concat_processing.append(dir_path)
            needs_audio_processing.append(dir_path)
        
        # Check for audio isolation and transcription
        # Update to check for .json instead of .pkl
        if not (dir_path / 'processed').exists() and (dir_path / 'audio').exists():
            if not dir_path in needs_audio_processing:
                needs_audio_processing.append(dir_path)

    return needs_concat_processing, needs_audio_processing

# Read data dir file
with open('data_management/main_data_dir.txt', 'r') as f:
    data_dir = Path(f.read().strip())
    print(f'Using data directory: {data_dir}')

needs_concat_processing, needs_audio_processing = get_folders_needing_processing(data_dir)

print(f'Running concatenation and alignment on {len(needs_concat_processing)} folders:')
for dir_path in needs_concat_processing:
    print(dir_path)

for d, dir_path in enumerate(needs_concat_processing, 1):
    print(f'PROCESSING {dir_path} ({d}/{len(needs_concat_processing)})')
    try:
        process_folder(dir_path)
    except Exception as e:
        print(f'Error processing {dir_path}: {e}')

print(f'\nRunning audio isolation and transcription on {len(needs_audio_processing)} folders:')
for dir_path in needs_audio_processing:
    print(dir_path)

for d, dir_path in enumerate(needs_audio_processing, 1):
    print(f'Processing {dir_path} ({d}/{len(needs_audio_processing)})')
    try:
        extract_transcripts(dir_path)
    except Exception as e:
        print(f'Error processing {dir_path}: {e}')

