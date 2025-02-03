from pathlib import Path
import pandas as pd
from qualtrics.pull_qualtrics import get_all_responses, format_responses
import logging
import sys
from tqdm import tqdm
import os
import json
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('survey_processing.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def main():
    try:
        main_dir = Path('/safestore/users/landry/SCRAP/data/andromeda_storage/conversations_unconstrained')
        if not main_dir.exists():
            raise FileNotFoundError(f"Main directory not found: {main_dir}")
        
        all_sessions = list(main_dir.glob('*'))
        all_sessions = [s for s in all_sessions if s.is_dir() and not 'remove' in s.name]
        if not all_sessions:
            raise ValueError("No valid session directories found")

        ok = input(f'About to pull surveys for {len(all_sessions)} sessions. Continue? (y/n)')
        if ok != 'y':
            logging.info('Exiting script')
            return

        letters = ['A', 'B', 'C', 'D']
        phases = ['pre', 'post']
        n_participants = [2, 3, 4]

        # Load all question keys at the start
        question_keys = {}
        print(os.getcwd())

        for n in n_participants:
            try:
                question_keys[n] = {
                    'pre': load_json(f'qualtrics/pre_{n}key.json'),
                    'post': load_json(f'qualtrics/post_{n}key.json')
                }
            except FileNotFoundError as e:
                logging.error(f"Question key file not found for {n} participants: {e}")
                raise

        # Initialize data structure
        all_data = {}
        for phase in phases:
            all_data[phase] = {}
            for n in n_participants:
                try:
                    all_data[phase][n] = {}
                    all_data[phase][n]['data'] = get_all_responses(phase=phase, n=n)
                    if all_data[phase][n]['data'] is None:
                        raise ValueError(f"No data returned for {phase} phase, {n} participants")
                    else:
                        print(f"Retrieved {phase} data for all {n}-participant sessions. Shapes: {all_data[phase][n]['data'].shape}")
                except Exception as e:
                    logging.error(f"Error getting responses for {phase} phase, {n} participants: {e}")
                    raise

        # Process each session
        for session in tqdm(all_sessions, desc='Processing sessions'):
            try:
                date, exp_num = session.name.split('_')[0], session.name.split('_')[1]
                survey_dir = session / 'surveys'
                audio_dir = session / 'audio'

                # Create survey directory if it doesn't exist
                survey_dir.mkdir(exist_ok=True)

                # Get number of participants from WAV files
                wav_files = list(audio_dir.glob('*.WAV'))
                if not wav_files:
                    logging.warning(f"No WAV files found in {audio_dir}")
                    continue
                n = len(wav_files)

                if n not in n_participants:
                    logging.warning(f"Unexpected number of participants ({n}) in {session}")
                    continue

                pre_data = all_data['pre'][n]['data']
                post_data = all_data['post'][n]['data']

                # Filter data for specific date and experiment
                pre_data = pre_data[(pre_data['StartDate'].str.contains(date)) & (pre_data['Q13'].str.contains(exp_num))]
                post_data = post_data[(post_data['StartDate'].str.contains(date)) & (post_data['Q13'].str.contains(exp_num))]

                if pre_data.empty or post_data.empty:
                    logging.warning(f"No survey data found for session {session.name}")
                    continue

                # Process each participant
                for letter in letters[:n]:
                    try:
                        participant_pre_data = pre_data[pre_data['Q7']==letter]
                        participant_post_data = post_data[post_data['Q7']==letter]

                        if participant_pre_data.empty or participant_post_data.empty:
                            logging.warning(f"No data found for participant {letter} in session {session.name}")
                            continue

                        # Format the responses using the question keys
                        formatted_pre = format_responses(participant_pre_data, question_keys[n]['pre'])
                        formatted_post = format_responses(participant_post_data, question_keys[n]['post'])

                        # Save the formatted data
                        formatted_pre.to_csv(survey_dir / f'{letter}_pre_formatted.csv', index=False)
                        formatted_post.to_csv(survey_dir / f'{letter}_post_formatted.csv', index=False)
                        
                        logging.info(f"Successfully processed participant {letter} in session {session.name}")

                    except Exception as e:
                        logging.error(f"Error processing participant {letter} in session {session.name}: {e}")
                        continue

            except Exception as e:
                logging.error(f"Error processing session {session.name}: {e}")
                continue

    except Exception as e:
        logging.error(f"Fatal error in script execution: {e}")
        raise

    logging.info("Script completed successfully")


if __name__ == "__main__":
    main()


