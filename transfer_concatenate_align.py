from file_transfer import run_transfer
from video.video import apply_concatenation
from alignment.align import align_data

# run the file transfer and then get the paths to the files
data_folder = run_transfer()

# concatenate the video files
concat_video_files = apply_concatenation(data_folder)

# align the data
# get microphone paths
mic_paths = data_folder / 'audio'
mic_paths = [str(i) for i in mic_paths.iterdir() if Path(i).suffix.lower() == '.wav']
align_data(concat_files, mic_paths)





