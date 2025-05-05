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

def needs_transcription(data_dir):
    """Check if a directory needs transcription by looking for existing JSON files."""
    processed_path = data_dir / 'processed'
    existing_jsons = set(f.stem.split('_')[0] for f in processed_path.glob('*_transcript.json'))
    return len(existing_jsons) < len(letter_assignments)

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
    print(f'Checking {len(list(main_dir.iterdir()))} directories for missing transcripts...')
    
    # Find directories that need transcription
    dirs_to_process = [d for d in main_dir.iterdir() if d.is_dir() and needs_transcription(d)]
    
    if not dirs_to_process:
        print("No directories found that need transcription.")
        return
        
    print("\nThe following directories need transcription:")
    for d in dirs_to_process:
        print(f"- {d.name}")
    
    confirmation = input("\nDo you want to proceed with transcription? (y/n): ")
    if confirmation.lower() != 'y':
        print("Transcription cancelled.")
        return
    
    print("\nStarting transcription...")
    for subdir in tqdm(dirs_to_process):
        print(f'\nProcessing directory: {subdir.name}')
        try:
            extract_transcripts(subdir)
        except Exception as e:
            print(f'Error extracting transcripts for {subdir}: {e}')

if __name__ == '__main__':
    main()



