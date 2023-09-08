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

    concat_dir = camera_path / "concatenated"
    os.makedirs(concat_dir, exist_ok=True)
    filename = f'{str(concat_dir)}/{cam_identity}_concatenated.mp4'
    concat_command = (f'ffmpeg -f concat -safe 0 -i {str(add_text)} -c copy {filename}')

    print(f"Concatenating {cam_identity}...")
    subprocess.run(concat_command, shell=True)