from voicolate.isolate import isolate_audio
from voicolate.transcribe import transcribe
from pathlib import Path
import joblib

letter_assignments = ['A', 'B', 'C', 'D']

def extract_transcripts(data_dir):
    data_dir = Path(data_dir)
    derivative_path = data_dir / 'derivatives'
    audio_files = [str(i) for i in derivative_path.iterdir() if Path(i).suffix == '.wav']
    audio_files.sort()
    processed_path = data_dir / 'processed'
    # make dir
    processed_path.mkdir(exist_ok=True)
    # isolate
    isolated_files = isolate_audio(audio_files, save_files=True, output_path=str(processed_path))
    isolated_files.sort()
    # transcribe
    transcripts = []
    for file in isolated_files:
        transcript = transcribe(file)
        transcripts.append(transcript)
    # save transcripts
    for letter, transcript in zip(letter_assignments, transcripts):
        joblib.dump(transcript, processed_path / f'{letter}_transcript.pkl')



