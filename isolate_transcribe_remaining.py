#!/usr/bin/env python
# coding: utf-8

"""
This script performs audio isolation and transcription on folders that don't contain '_remove' in their name.
Includes an overwrite flag to re-run isolation and transcription with updated pipeline.
"""

from isolate_and_transcribe import extract_transcripts
from pathlib import Path
import os
import json
from tqdm import tqdm
import argparse

def get_folders_needing_processing(data_dir, overwrite=False):
    """
    Get folders that need audio isolation and transcription processing.
    
    Args:
        data_dir: Path to the main data directory
        overwrite: If True, process all folders regardless of existing files
        
    Returns:
        List of folder paths that need processing
    """
    needs_audio_processing = []

    pbar = tqdm(list(data_dir.iterdir()), desc='Checking folders')
    for dir_path in data_dir.iterdir():
        pbar.update(1)
        
        # Skip if not a directory
        if not dir_path.is_dir():
            continue
            
        # Skip folders containing '_remove' in their name
        if '_remove' in dir_path.name:
            continue
        
        # Check if audio directory exists
        audio_dir = dir_path / 'audio'
        if not audio_dir.is_dir():
            continue
        
        # If overwrite flag is set, add all folders with audio
        if overwrite:
            needs_audio_processing.append(dir_path)
            continue
        
        # Otherwise, only add folders that haven't been processed yet
        # Check for audio isolation and transcription outputs
        processed_dir = dir_path / 'processed'
        isolated_files = list(processed_dir.glob('*_isolated.wav')) if processed_dir.exists() else []
        
        if len(isolated_files) == 0:
            needs_audio_processing.append(dir_path)

    return needs_audio_processing

def main():
    parser = argparse.ArgumentParser(
        description='Perform audio isolation and transcription on remaining folders (excluding those with "_remove" in name)'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Re-run isolation and transcription even if files already exist'
    )
    args = parser.parse_args()

    # Read data dir file
    with open('data_management/main_data_dir.txt', 'r') as f:
        data_dir = Path(f.read().strip())
        print(f'Using data directory: {data_dir}')

    print(f'Overwrite mode: {"ON" if args.overwrite else "OFF"}')
    needs_audio_processing = get_folders_needing_processing(data_dir, overwrite=args.overwrite)

    print(f'\nRunning audio isolation and transcription on {len(needs_audio_processing)} folders:')
    for dir_path in needs_audio_processing:
        print(f'  - {dir_path.name}')

    if len(needs_audio_processing) == 0:
        print('No folders need processing.')
        return

    for d, dir_path in enumerate(needs_audio_processing, 1):
        print(f'\nProcessing {dir_path.name} ({d}/{len(needs_audio_processing)})')
        try:
            extract_transcripts(dir_path)
            print(f'✓ Successfully processed {dir_path.name}')
        except Exception as e:
            print(f'✗ Error processing {dir_path.name}: {e}')

    print(f'\nCompleted processing {len(needs_audio_processing)} folders.')

if __name__ == '__main__':
    main()

