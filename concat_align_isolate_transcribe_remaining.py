#!/usr/bin/env python
# coding: utf-8

"""
This script will fully process all data from the main data directory, including concatenation, alignment, audio isolation, and transcription.
"""

from extract_transcripts import extract_transcripts
from concatenate_align import process_folder
from pathlib import Path
import os
from tqdm import tqdm

# read data dir file
with open('data_management/main_data_dir.txt', 'r') as f:
    data_dir = Path(f.read())

needs_concat_processing = [f for f in data_dir.iterdir() if f.is_dir() and not any([f.name == 'cam1_concatenated_trimmed.mp4' for f in f.rglob('*')])]
# keep only folders that contain an audio directory
needs_concat_processing = [f for f in needs_concat_processing if any([f.name == 'audio' for f in f.iterdir()])]
print(f'Running concatenation and alignment on {len(needs_concat_processing)} folders:\n')
print(needs_concat_processing)

for d, dir in enumerate(needs_concat_processing):
    print(f'PROCESSING {dir} ({d+1}/{len(needs_concat_processing)})')
    process_folder(dir)

# retain only top-level folders within data_dir have not had isolation performed on them
needs_audio_processing = [f for f in data_dir.iterdir() if f.is_dir() and not any([f.name == '0_isolated.wav' for f in f.rglob('*')])]
needs_audio_processing = [f for f in needs_audio_processing if (f / 'audio').is_dir() and len([f for f in (f / 'audio').iterdir() if f.suffix.lower() == '.wav']) > 0]
# ensure that there is a file called 'cam1_concatenated_trimmed.mp4' in each folder's derivatives directory
needs_audio_processing = [f for f in needs_audio_processing if (f / 'derivatives' / 'cam1_concatenated_trimmed.mp4').exists()]

print(f'Running audio isolation and transcription on {len(needs_audio_processing)} folders:\n')
print(needs_audio_processing)
for d, dir in enumerate(needs_audio_processing):
    print(f'Processing {dir} ({d}/{len(needs_audio_processing)} remaining)')
    extract_transcripts(dir)

