#!/usr/bin/env python
# coding: utf-8


from extract_transcripts import extract_transcripts
from pathlib import Path
import os
from tqdm import tqdm
from scipy.io import wavfile


data_dir = Path('/safestore/users/landry/SCRAP/data/andromeda_storage/conversations_unconstrained')
# retain only top-level folders within data_dir that contain a file called 'cam1_concatenated_trimmed.mp4' somewhere within them, recursively
needs_processing = [f for f in data_dir.iterdir() if f.is_dir() and not any([f.name == '0_isolated.wav' for f in f.rglob('*')])]
needs_processing = [f for f in needs_processing if (f / 'audio').is_dir() and len([f for f in (f / 'audio').iterdir() if f.suffix.lower() == '.wav']) > 0]
needs_processing


for d, dir in enumerate(needs_processing):
    print(f'Processing {dir} ({d}/{len(needs_processing)} remaining)')
    extract_transcripts(dir)

