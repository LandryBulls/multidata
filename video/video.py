import os
from pathlib import Path
import subprocess

def concatenate(cam_directory):
    cam_identity = os.path.basename(cam_directory)
    camera_path = Path(cam_directory)
    to_concat = [i for i in camera_path.iterdir() if Path(i).suffix.lower() == '.mp4'].sort()
    add_text = camera_path / 'concat_history.txt'

    with open(add_text, "w") as f:
        for v in to_concat:
            f.write('file ' + str(v) + "\n")

    # just put the .mp4's in the same directory, then put the trimmed files in derivatives later
    filename = f'{cam_identity}_concatenated.mp4'
    concat_command = (f'ffmpeg -f concat -safe 0 -i {str(add_text)} -c copy {camera_path / filename}')

    print(f"Concatenating {cam_identity}...")
    subprocess.run(concat_command, shell=True)
    return filename

def to_equirectangluar(cam_directory):
    cam_dir = Path(cam_directory)
    files = [i for i in cam_dir.iterdir() if Path(i).suffix == '.360']
    for file in files:
        filename = os.path.basename(file)[:-4]
        output_name = str(cam_directory / f'{filename}_equirectangular.mp4')
        command = f"ffmpeg -hwaccel opencl -v verbose -filter_complex '[0:0]format=yuv420p,hwupload[a] , [0:5]format=yuv420p,hwupload[b], [a][b]gopromax_opencl, hwdownload,format=yuv420p' -i {str(file)} -c:v libx264 -pix_fmt yuv420p -map_metadata 0 -map 0:a -map 0:3 {output_name}"
        subprocess.run(command, shell=True, stdout=open(os.devnull, 'wb'))


def apply_concatenation(data_dir):
    # get all camera directories
    cam_directories = [i for i in Path(data_dir).iterdir() if 'cam' in str(i)]
    #derivative_path = data_dir / 'derivatives'
    concat_files = []
    for cam in cam_directories:
        if '360' in str(cam):
            # do fancy 360 concatentation
            to_equirectangluar(cam)
        concat_file = concatenate(cam)
        concat_files.append(concat_file)

    # returns a list of filenames of the concatenated videos
    return concat_files
