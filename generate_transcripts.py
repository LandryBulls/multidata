"""
Extracts transcripts from audio files in a directory.
Assumes that video has been concatenated and aligned. 
"""


from voicolate.isolate import isolate_audio
from voicolate.transcribe import transcribe
from pathlib import Path
import json
from scipy.io import wavfile
from tqdm import tqdm

letter_assignments = ['A', 'B', 'C', 'D']

def extract_transcripts(data_dir):
    processed_path = data_dir / 'processed'
    audio_paths = [str(i) for i in list(processed_path.glob('TRACK0*_trimmed_isolated_v2.wav')) if 'isolated' in i.name]
    audio_paths.sort()
    transcripts = []
    for file in audio_paths:
        transcript = transcribe(file)
        transcripts.append(transcript)
    # save transcripts as JSON instead of pickle
    for letter, transcript in zip(letter_assignments, transcripts):
        json_path = processed_path / f'{letter}_transcript.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)

def main():
    main_dir = Path('/safestore/users/landry/SCRAP/data/andromeda_storage/conversations_unconstrained')
    print(f'Processing {len(list(main_dir.iterdir()))} directories')
    dirs = [i for i in main_dir.iterdir()][19:]
    for subdir in tqdm(dirs):
        if subdir.is_dir():
            print(f'\nProcessing directory: {subdir.name}')
            try:
                extract_transcripts(subdir)
            except Exception as e:
                print(f'Error extracting transcripts for {subdir}: {e}')

if __name__ == '__main__':
    main()



