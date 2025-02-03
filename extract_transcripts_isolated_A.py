"""
Extracts transcripts from audio files in a directory.
Assumes that video has been concatenated and aligned. 
"""

from voicolate.transcribe import transcribe
from pathlib import Path
import joblib
from scipy.io import wavfile

letter_assignments = ['A', 'B', 'C', 'D']

def extract_transcripts(data_dir):
    data_dir = Path(data_dir)
    processed_path = data_dir / 'processed'
    # isolate
    afile = processed_path / '0_isolated.wav'
    if afile.exists():
        transcript = transcribe(afile)
        joblib.dump(transcript, processed_path / 'A_transcript.pkl')

data_dir = Path('/safestore/users/landry/SCRAP/data/andromeda_storage/conversations_unconstrained')
dirs = [f for f in data_dir.iterdir() if f.is_dir()]
dirs = [i for i in dirs if (i / 'processed' / 'A_transcript.pkl').exists()]
print(f'Found {len(dirs)} directories.')
ok = input('Continue? (y/n) ')

if ok == 'y':
    for directory in dirs:
        print(f'Processing {directory.name}...')
        extract_transcripts(directory)
    print('Done.')







