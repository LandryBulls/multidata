from voicolate.isolate import isolate
from pathlib import Path
import os
from tqdm import tqdm
from scipy.io import wavfile
import glob
import logging
from datetime import datetime

# Configure logging
current_date = datetime.now().strftime('%Y%m%d')
log_filename = f'audio_isolation_{current_date}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
    logging.StreamHandler()  # This will also print to console
    ]
)

def run_isolation(session_dir):
    session_dir = Path(session_dir)
    derivative_path = session_dir / 'derivatives'
    audio_files = glob.glob(str(derivative_path / 'TRACK0*_trimmed.wav'))
    audio_files.sort()
    # checking if audio files follow the naming convention and order of : TRACK01.WAV, TRACK02.WAV, etc.
    print(f"Found audio files: {[Path(f).stem for f in audio_files]}")
    for i, file in enumerate(audio_files):
        if Path(file).stem != f'TRACK0{i+1}_trimmed':
            logging.error(f'Audio files do not follow the naming convention and order of : TRACK01_trimmed.WAV, TRACK02_trimmed.WAV, etc. for {session_dir}')
            raise ValueError(f'Audio files do not follow the naming convention and order of : TRACK01_trimmed.WAV, TRACK02_trimmed.WAV, etc. for {session_dir}')

    if not audio_files:
        logging.warning(f'No trimmed audio files found in {derivative_path}, skipping.')
        return

    processed_path = session_dir / 'processed'
    processed_path.mkdir(parents=True, exist_ok=True)

    audio_filenames = [str(Path(i).stem) for i in audio_files]
    isolated_files = isolate(audio_files, save_files=False, output_path=str(processed_path))
    for file, arr in zip(audio_filenames, isolated_files):
        wavfile.write(str(processed_path / f'{file}_isolated_v2.wav'), 44100, arr)

def main():
    data_dir = Path('/safestore/users/landry/SCRAP/data/andromeda_storage/conversations_unconstrained')
    allsessions = [str(i) for i in data_dir.iterdir() if i.is_dir()]
    
    # Filter sessions that don't have isolated files
    sessions_to_process = []
    for session in allsessions:
        session_path = Path(session)
        processed_path = session_path / 'processed'
        if not processed_path.exists() or not any('isolated_v2.wav' in str(f) for f in processed_path.glob('*')):
            sessions_to_process.append(session)

    ok = input(f'Processing {len(sessions_to_process)} sessions. Continue? (y/n)')
    if ok.lower() != 'y':
        return
    for session in tqdm(sessions_to_process):
        logging.info(f'Processing {session}')
        try:
            run_isolation(session)
        except Exception as e:
            error_msg = f'Error in {session}: {str(e)}'
            logging.error(error_msg)
            print(error_msg + '. Skipping...')

if __name__ == '__main__':
    logging.info('Starting audio isolation process')
    main()
    logging.info('Finished audio isolation process')




