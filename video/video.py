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

    to_concat = [i for i in camera_path.iterdir() if Path(i).suffix.lower() == '.mp4']
    to_concat.sort()
    add_text = dest_directory/ f'{cam_identity}_concat_history.txt'

    with open(add_text, "w") as f:
        for v in to_concat:
            f.write('file ' + str(v) + "\n")

    # just put the .mp4's in the same directory, then put the trimmed files in derivatives later
    filename = f'{cam_identity}_concatenated.mp4'
    concat_command = (f'ffmpeg -f concat -safe 0 -i {str(add_text)} -c copy {dest_directory / filename}')

    print(f"Concatenating {cam_identity}...")
    subprocess.run(concat_command, shell=True)
    return filename

def to_equirectangluar(cam_directory, dest_directory):
    dest_directory = Path(dest_directory)
    cam_dir = Path(cam_directory)
    files = [i for i in cam_dir.iterdir() if Path(i).suffix == '.360']
    for file in files:
        filename = os.path.basename(file)[:-4]
        output_name = str(dest_directory / f'{filename}_equirectangular.mp4')
        command = f"ffmpeg -hwaccel opencl -v verbose -filter_complex '[0:0]format=yuv420p,hwupload[a] , [0:5]format=yuv420p,hwupload[b], [a][b]gopromax_opencl, hwdownload,format=yuv420p' -i {str(file)} -c:v libx264 -pix_fmt yuv420p -map_metadata 0 -map 0:a -map 0:3 {output_name}"
        subprocess.run(command, shell=True, stdout=open(os.devnull, 'wb'))


def apply_concatenation(data_dir):
    data_dir = Path(data_dir)
    derivative_path = make_derivative_folder(data_dir)
    # get all camera directories
    cam_directories = [i for i in Path(data_dir).iterdir() if 'cam' in str(i)]
    concat_files = []
    for cam in cam_directories:
        if '360' in str(cam):
            # do fancy 360 concatenation (not doing this for now until I find a better solution)
            #to_equirectangluar(cam, cam)
            None
        concat_file = concatenate(cam, derivative_path)
        concat_files.append(concat_file)

    # returns a list of filenames of the concatenated videos
    return concat_files
