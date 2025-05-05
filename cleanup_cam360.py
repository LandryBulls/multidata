#!/usr/bin/env python3

"""
This script searches for and deletes files and directories containing 'cam360' in their names.
It requires user confirmation before performing any deletions.
"""

import os
from pathlib import Path
from glob import glob
import sys
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import multiprocessing

# Directories to skip during search
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv'}

def search_in_directory(directory, pattern='**/cam360*'):
    """
    Search for cam360 files in a specific directory using glob.
    
    Args:
        directory (Path): Directory to search in
        pattern (str): Glob pattern to match
        
    Returns:
        tuple: Lists of (files, directories) containing 'cam360' in their names
    """
    try:
        matches = list(Path(directory).glob(pattern))
        files = [p for p in matches if p.is_file()]
        dirs = [p for p in matches if p.is_dir()]
        return files, dirs
    except Exception as e:
        print(f"Error searching in {directory}: {e}")
        return [], []

def find_cam360_files(base_dir):
    """
    Find all files and directories containing 'cam360' in their names using parallel processing.
    
    Args:
        base_dir (Path): Base directory to start the search from
        
    Returns:
        tuple: Lists of (files, directories) containing 'cam360' in their names
    """
    base_dir = Path(base_dir)
    
    # Get immediate subdirectories that we want to search
    subdirs = [d for d in base_dir.iterdir() if d.is_dir() and d.name not in SKIP_DIRS]
    
    # Search the base directory first
    base_files, base_dirs = search_in_directory(base_dir)
    
    # Use parallel processing for subdirectories
    num_processes = max(1, multiprocessing.cpu_count() - 1)  # Leave one CPU free
    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        results = list(executor.map(search_in_directory, subdirs))
    
    # Combine results
    all_files = base_files
    all_dirs = base_dirs
    
    for files, dirs in results:
        all_files.extend(files)
        all_dirs.extend(dirs)
    
    return all_files, all_dirs

def main():
    # Read the main data directory from the same location as file_transfer.py
    try:
        dirpath = Path(os.path.dirname(os.path.realpath(__file__))) / 'data_management' / 'main_data_dir.txt'
        with open(dirpath, 'r') as f:
            main_data_dir = Path(f.readline().strip())
    except FileNotFoundError:
        print("Error: Could not find main_data_dir.txt")
        sys.exit(1)

    print(f"Searching for 'cam360' files in: {main_data_dir}")
    
    # Find all cam360 files and directories
    files_to_delete, dirs_to_delete = find_cam360_files(main_data_dir)
    
    if not files_to_delete and not dirs_to_delete:
        print("No files or directories containing 'cam360' were found.")
        return
    
    # Print all found items
    print("\nFound the following items containing 'cam360':")
    print("\nFiles:")
    for file in files_to_delete:
        print(f"  - {file}")
    
    print("\nDirectories:")
    for directory in dirs_to_delete:
        print(f"  - {directory}")
    
    # Ask for confirmation
    total_items = len(files_to_delete) + len(dirs_to_delete)
    print(f"\nTotal items to delete: {total_items}")
    
    confirmation = input("\nAre you sure you want to delete these items? (yes/no): ")
    if confirmation.lower() != 'yes':
        print("Operation cancelled.")
        return
    
    # Delete the items
    print("\nDeleting items...")
    
    for file in tqdm(files_to_delete, desc="Deleting files"):
        try:
            file.unlink()
            print(f"Deleted file: {file}")
        except Exception as e:
            print(f"Error deleting {file}: {e}")
    
    # Delete directories in reverse order (deepest first)
    for directory in sorted(dirs_to_delete, reverse=True):
        try:
            if directory.exists():  # Check again in case parent was already deleted
                if directory.is_dir():
                    directory.rmdir()  # This will only work if directory is empty
                    print(f"Deleted directory: {directory}")
        except Exception as e:
            print(f"Error deleting {directory}: {e}")
    
    print("\nCleanup complete!")

if __name__ == "__main__":
    main() 