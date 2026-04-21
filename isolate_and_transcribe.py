"""
Extracts transcripts from audio files in a directory.
Assumes that video has been concatenated and aligned. 
"""


from voicolate.isolate import isolate
from voicolate.transcribe import transcribe
from pathlib import Path
import json
from scipy.io import wavfile
import numpy as np

letter_assignments = ['A', 'B', 'C', 'D']

def ensure_audio_lengths_match(audio_files):
    """
    Ensure all audio files have the same length by padding shorter ones with zeros.
    Returns the maximum length and a list of padded audio arrays.
    """
    audio_arrays = []
    lengths = []
    
    # Load all audio files and get their lengths
    for file in audio_files:
        sr, audio = wavfile.read(file)
        audio_arrays.append(audio)
        lengths.append(len(audio))
    
    # Find the maximum length
    max_length = max(lengths)
    
    # Pad shorter arrays with zeros
    padded_arrays = []
    for audio in audio_arrays:
        if len(audio) < max_length:
            padded = np.pad(audio, (0, max_length - len(audio)), 'constant')
            padded_arrays.append(padded)
        else:
            padded_arrays.append(audio)
    
    return padded_arrays, max_length

def extract_transcripts(data_dir):
    data_dir = Path(data_dir)
    derivative_path = data_dir / 'derivatives'
    # ignore hidden files
    audio_files = [str(i) for i in derivative_path.iterdir() if Path(i).suffix == '.wav' and not Path(i).name.startswith('.')]
    
    # check if audio files are all the same length
    audio_durations = []
    for file in audio_files:
        sr, audio = wavfile.read(file)
        audio_durations.append(len(audio)/sr)
    if len(set(audio_durations)) > 1:
        raise ValueError(f'Audio files for {data_dir} are not all the same length.')
    
    audio_files.sort()
    processed_path = data_dir / 'processed'
    # make dir
    processed_path.mkdir(exist_ok=True)
    
    # Check for existing Wiener cache and handle length mismatches
    cache_dir = processed_path / 'wiener_cache'
    if cache_dir.exists():
        # Check if cached files have different lengths than current audio files
        cached_files = list(cache_dir.glob('*_wiener.wav'))
        if cached_files:
            # Get current audio file length
            sr, current_audio = wavfile.read(audio_files[0])
            current_length = len(current_audio)
            
            # Check cached file length
            sr_cached, cached_audio = wavfile.read(cached_files[0])
            cached_length = len(cached_audio)
            
            if current_length != cached_length:
                print(f"Warning: Cached Wiener files have different length ({cached_length}) than current audio files ({current_length})")
                print("Removing cached files to force recomputation...")
                # Remove cached files to force recomputation
                for cached_file in cached_files:
                    cached_file.unlink()
    
    try:
        # isolate
        isolated_files = isolate(audio_files, save_files=True, output_path=str(processed_path))
        isolated_files.sort()
    except Exception as e:
        if "operands could not be broadcast together" in str(e):
            print(f"Broadcasting error detected: {e}")
            print("Attempting to fix by clearing Wiener cache and recomputing...")
            # Clear the cache and try again
            if cache_dir.exists():
                import shutil
                shutil.rmtree(cache_dir)
            # Try again
            isolated_files = isolate(audio_files, save_files=True, output_path=str(processed_path))
            isolated_files.sort()
        else:
            raise e
    
    # transcribe
    transcripts = []
    for file in isolated_files:
        transcript = transcribe(file)
        transcripts.append(transcript)
    # save transcripts as JSON instead of pickle
    for letter, transcript in zip(letter_assignments, transcripts):
        json_path = processed_path / f'{letter}_transcript.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)



