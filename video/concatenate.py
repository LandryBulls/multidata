import os
from pathlib import Path
import subprocess

def concatenate(cam_directory):
    cam_identity = os.path.basename(cam_directory)
    camera_path = Path(cam_directory)
    to_concat = [i for i in camera_path.iterdir() if Path(i).suffix.lower() == '.mp4']
    add_text = camera_path / 'concat_history.txt'

    with open(add_text, "w") as f:
        for v in to_concat:
            f.write('file ' + str(v) + "\n")

    #concat_dir = camera_path / "concatenated"
    #os.makedirs(concat_dir, exist_ok=True)
    filename = f'{cam_identity}_concatenated.mp4'
    concat_command = (f'ffmpeg -f concat -safe 0 -i {str(add_text)} -c copy {filename}')

    print(f"Concatenating {cam_identity}...")
    subprocess.run(concat_command, shell=True)
    return filename

def apply_concatenation(data_dir):
    # get all camera directories
    cam_directories = [i for i in Path(data_dir).iterdir() if 'cam' in str(i)]
    #derivative_path = data_dir / 'derivatives'
    concat_files = []
    for cam in cam_directories:
        if '360' in str(cam):
            # do fancy 360 concatentation
            None
        else:
            concat_file = concatenate(cam)
            concat_files.append(concat_file)

    return concat_files
