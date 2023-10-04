from video.video import apply_concatenation
from alignment.align import align_data

def process_folder(data_dir):
    conatenated_video_files = apply_concatenation(data_dir)
    align_data(data_dir)