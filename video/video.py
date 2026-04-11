import os
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

    concat_command = f'ffmpeg -y -f concat -safe 0 -i {str(add_text)} -map 0:v -map 0:a:0 -c copy {dest_directory / filename}'


    print(f"Concatenating {cam_identity}...")
    subprocess.run(concat_command, shell=True)
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
