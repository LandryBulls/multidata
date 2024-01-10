#!/usr/bin/env python
# coding: utf-8


from concatenate_align import process_folder
from pathlib import Path
import os
from tqdm import tqdm
import librosa
from scipy.io import wavfile

dirpath = '/safestore/users/landry/SCRAP/packages/multidata/data_dir.txt'
with open(dirpath, 'r') as f:
    main_data_dir = f.readline().strip()

data_dir = Path(main_data_dir)
# retain only top-level folders within data_dir that contain a file called 'cam1_concatenated_trimmed.mp4' somewhere within them, recursively
needs_processing = [f for f in data_dir.iterdir() if f.is_dir() and not any([f.name == 'cam1_concatenated_trimmed.mp4' for f in f.rglob('*')])]
# keep only folders that contain an audio directory
needs_processing = [f for f in needs_processing if any([f.name == 'audio' for f in f.iterdir()])]
needs_processing

for d, dir in enumerate(needs_processing):
    print(f'PROCESSING {dir} ({d+1}/{len(needs_processing)})')
    process_folder(dir)


