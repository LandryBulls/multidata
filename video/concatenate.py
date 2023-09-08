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

    concat_command = (f"ffmpeg -f concat -safe 0 -i {str(add_text)} -c copy "
                      f"{str(cam_identity / 'concatenated' / f'{cam_identity}_concatenated.mp4')}")
    print(f"Concatenating {cam_identity}...")
    subprocess.run(concat_command, shell=True)
