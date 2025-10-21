#!/usr/bin/env python
# coding: utf-8


"""
This script contains functions for transferring data from the four connected SD cards and organizing them into
experiment folders. It uses the Qualtrics API to pull survey data from Qualtrics and save it to the experiment folder
(imported from separate qualtrics script).

It creates the following directory structure. The top-level directory is organized by date + experiment number, where
the experiment number is the nth experiment of the day. The experiment number is zero-padded to three digits.

YYYY-MM-DD_XXX
    - cam1
    - cam2
    - 360cam
    - audio

The the assigment of the monocular cameras to cameras 1 and 2 is arbitrary. The 360 camera is always assigned to the
360cam folder.
"""


import os
import subprocess
from glob import glob
from pathlib import Path
import shutil
import sys
import time
from io import BytesIO
from tqdm import tqdm
import warnings
from qualtrics.pull_qualtrics import get_survey_data

dirpath = Path(os.path.dirname(os.path.realpath(__file__))) / 'main_data_dir.txt'
    
with open(dirpath, 'r') as f:
    main_data_dir = f.readline().strip()

def transfer_file(source, dest_path):
    """
    Transfer a file from a source to a destination path.
    :param source: Path to the file to transfer.
    :type source:
    :param dest_path:
    :type dest_path:
    :return:
    :rtype:
    """
    fsize = int(os.path.getsize(source))
    dest = os.path.join(dest_path, os.path.basename(source))
    with open(source, 'rb') as f:
        with open(dest, 'ab') as n:
            with tqdm(ncols=60, total=fsize, bar_format='{l_bar}{bar} | Remaining: {remaining}') as pbar:
                buffer = bytearray()
                while True:
                    buf = f.read(8192)
                    n.write(buf)
                    if len(buf) == 0:
                        break
                    buffer += buf
                    pbar.update(len(buf))

def get_all_files(card_path):
    """
    Get all files on a card.
    :param card_path:
    :type card_path:
    :return:
    :rtype:
    """
    all_files = []
    for root, dirs, files in os.walk(card_path):
        for file in files:
            if '.Trash' not in root:
                all_files.append(os.path.join(root, file))
    return all_files

# get paths of SD cards connected
def get_sd_cards():
    """
    Get the paths of the SD cards connected to the computer. Checks what platform the script is running on and uses
    different methods for getting the SD card paths depending on the platform. This function also organizes
    the files on the SD cards into a dictionary. This is the step that determines which card contains what data
    (e.g. which card contains the 360 footage, which card contains the audio, etc.).
    :return:
    :rtype:
    """
    if sys.platform == 'darwin':
        connected_sd_cards = [Path(card) for card in glob('/Volumes/Untitled*/')]
    elif sys.platform == 'win32':
        connected_sd_cards = [Path(card) for card in glob('E:/')]
    elif sys.platform == 'linux':
        user = os.environ['USER']
        connected_sd_cards = [Path(card) for card in glob(f'/media/{user}/*')]
    else:
        # throw error if platform is unknown
        raise OSError('Unknown platform')

    card_id = {}
    # card label and files to download
    data_incoming = {''}
    mono_cam_count = 0

    for card in connected_sd_cards:
        allfiles = get_all_files(card)
        if any(['.360' in file for file in allfiles]):
            files = [file for file in allfiles if '.360' in file]
            # now add the mp4s also
            files += [file for file in allfiles if '.mp4' in file.lower()]
            card_id['360cam'] = {'card_path': str(card), 'files': files}
        elif any(['.mp4' in file.lower() for file in allfiles]) and not any(['TRACK' in file for file in allfiles]) and not any(['.360' in file for file in allfiles]):
            mono_cam_count += 1
            files = [file for file in allfiles if '.mp4' in file.lower()]
            card_id[f'cam{mono_cam_count}'] = {'card_path': str(card), 'files': files}
        elif any(['TRACK' in file for file in allfiles]):
            # TO DO: make sure audio files recorded on same date as video files
            files = [file for file in allfiles if 'TRACK' in file]
            card_id['audio'] = {'card_path': card, 'files': files}
        else:
            print(f'Unknown card: {card} contains the following files:')
            print(allfiles)

    assert len(card_id) == 4, f'Not all cards are connected\n Connected cards: {card_id.keys()}'

    return card_id

def get_date_exp_from_user():
    """
    Prompt the user to manually enter the date and experiment number for this recording session.
    :return: date_exp string in format YYYY-MM-DD_XXX
    :rtype: str
    """
    print('\nPlease enter the date and experiment number for this recording session.')
    print('Format: YYYY-MM-DD_XXX (e.g., 2024-10-21_001)')
    
    while True:
        date_exp = input('Enter date and experiment number: ').strip()
        
        # Basic validation: check format
        if '_' not in date_exp:
            print('Invalid format. Please use YYYY-MM-DD_XXX format (e.g., 2024-10-21_001)')
            continue
        
        parts = date_exp.split('_')
        if len(parts) != 2:
            print('Invalid format. Please use YYYY-MM-DD_XXX format (e.g., 2024-10-21_001)')
            continue
        
        date_part, exp_part = parts
        
        # Check date format (basic check)
        if len(date_part) != 10 or date_part.count('-') != 2:
            print('Invalid date format. Please use YYYY-MM-DD (e.g., 2024-10-21)')
            continue
        
        # Check experiment number format (should be 3 digits)
        if len(exp_part) != 3 or not exp_part.isdigit():
            print('Invalid experiment number. Please use 3 digits (e.g., 001, 002, etc.)')
            continue
        
        # If validation passes, confirm with user
        confirm = input(f'You entered: {date_exp}. Is this correct? (y/n): ')
        if confirm.lower() == 'y':
            return date_exp
        else:
            print('Let\'s try again...')

def delete_card(card_path):
    """
    Delete all files on an SD card (not working yet bc of permissions nuance w/ sd cards).
    :param card_path:
    :type card_path:
    :return:
    :rtype:
    """
    os.chmod(card_path, 0o777)
    shutil.rmtree(card_path)

def run_transfer():
    """
    Run the file transfer. This is the main function of this script. It integrates all the other functions in this
    script.
    :return:
    :rtype:
    """
    card_id = get_sd_cards()
    # get number of participants based on number of microphone tracks
    n_participants = len(card_id['audio']['files'])

    print(f'Found {n_participants} participants')

    # Get date and experiment number from user
    date_exp = get_date_exp_from_user()
    data_path = Path(main_data_dir) / date_exp
    
    dialog = 'The following files will be transferred:\n\n'
    for card in card_id:
        dialog += f'{card} has {len(card_id[card]["files"])} files:\n'
        for file in card_id[card]['files']:
            dialog += f'\t{file}\n'
        dialog += '\n'
    
    dialog += 'Ready to transfer? (y/n): '
    ok = input(dialog)

    if ok.lower() == 'y':
        transfer_approved = True
        pass
    else:
        transfer_approved = False
        raise OSError('User aborted transfer')
    
    if transfer_approved:
        os.makedirs(data_path, exist_ok=True)
        notes = input('Enter any notes for this session (press enter if none): ')
        with open(data_path / 'NOTE.txt', 'w') as f:
            f.write(notes)


        # print('##########################\n')
        # print('Pulling survey data from Qualtrics...\n')
        
        # try:
        #     survey_data, privacy_elections = get_survey_data(n_participants=n_participants, date=record_date, exp_num=exp_num)
        #     print('Survey data pulled from Qualtrics.\n')

        #     for part, survey in survey_data.items():
        #         pre, post = survey['pre'], survey['post']
        #         print(f'Participant {part} pre-survey: {pre.shape[0]} items')
        #         print(f'Participant {part} post-survey: {post.shape[0]} items')

        #     # make the survey folder
        #     survey_path = data_path / 'survey'
        #     os.makedirs(survey_path, exist_ok=True)

        #     for part, survey in survey_data.items():
        #         survey['raw_pre'].to_csv(survey_path / f'{part}_pre.csv', index=False)
        #         survey['raw_post'].to_csv(survey_path / f'{part}_post.csv', index=False)
        #         survey['pre'].to_csv(survey_path / f'{part}_pre_formatted.csv', index=False)
        #         survey['post'].to_csv(survey_path / f'{part}_post_formatted.csv', index=False)
        #         print(f'Participant {part} pre-survey: {survey["raw_pre"].shape[0]} items')
        #         print(f'Participant {part} post-survey: {survey["raw_post"].shape[0]} items')

        #     privacy_elections.to_csv(survey_path / 'privacy_elections.csv', index=False)
        #     print('Survey data saved to data folder.\n')
        # except Exception as e:
        #     print(f'Error occurred while pulling survey data: {str(e)}')
        #     print('Continuing with file transfer without survey data...\n')
        #     with open(data_path / 'SURVEY_ERROR.txt', 'w') as f:
        #         f.write(f'Error occurred while pulling survey data: {str(e)}\n')
        #         f.write(f'Survey data will need to be pulled separately using pull_qualtrics_to_folder()')

        # print('##########################\n')

        total_num_files = sum([len(card_id[card]['files']) for card in card_id])
        filenum = 0
        for card in card_id:
            dest_path = data_path / card
            os.mkdir(dest_path)
            for file in card_id[card]['files']:
                filenum += 1
                print(f'\n\nTransferring file {filenum} of {total_num_files} files\n')
                print(f'Source: {file}\n')
                print(f'Destination: {dest_path}/{os.path.basename(file)}\n')
                transfer_file(file, dest_path)

        print('##########################\n')
        print('Transfer complete!\n')
        print(f"Audiovisual data saved to {str(data_path)}\n")

        print('Data pull complete! Ok to remove drives now.\n')

        #
        # delete_approved = input('Delete files from SD cards? (y/n): ')
        # if delete_approved.lower() == 'y':
        #     for card in card_id:
        #         delete_card(card)
        #+     print('Files deleted from SD cards')
        # else:
        #     print('SD card file deletion aborted. Files still on SD cards.')

    return data_path

# function for pulling qualtrics data to an experiment that already has AV data
def pull_qualtrics_to_folder(data_path):
    data_path = Path(data_path)
    # get the number of participants from the number of audio files
    try:
        n_participants = len([file for file in os.listdir(data_path / 'audio') if '.wav' in file.lower()])
    except FileNotFoundError:
        warnings.warn('No audio files found.')
        n_participants = int(input('Enter number of participants: '))

    # get the date of the experiment
    date = os.path.basename(data_path).split('_')[0]
    # get the experiment number
    exp_num = os.path.basename(data_path).split('_')[1]
    # get the survey data
    survey_data, privacy_elections = get_survey_data(n_participants=n_participants, date=date, exp_num=exp_num)
    # make the survey folder
    survey_path = data_path / 'survey'
    os.makedirs(survey_path, exist_ok=True)

    for part, survey in survey_data.items():
        survey['raw_pre'].to_csv(survey_path / f'{part}_pre.csv', index=False)
        survey['raw_post'].to_csv(survey_path / f'{part}_post.csv', index=False)
        survey['pre'].to_csv(survey_path / f'{part}_pre_formatted.csv', index=False)
        survey['post'].to_csv(survey_path / f'{part}_post_formatted.csv', index=False)
        print(f'Participant {part} pre-survey: {survey["raw_pre"].shape[0]} items')
        print(f'Participant {part} post-survey: {survey["raw_post"].shape[0]} items')

    privacy_elections.to_csv(survey_path / 'privacy_elections.csv', index=False)

    print('Survey data saved to data folder\n')
    print('##########################\n')

    return data_path

# def pull_qualtrics_to_folders(list_of_data_paths):
#     data_paths = [Path(data_path) for data_path in list_of_data_paths]
#     # get the number of participants from the number of audio files
#     try:
#         n_participants = len([file for file in os.listdir(data_path / 'audio') if '.wav' in file.lower()])
#     except FileNotFoundError:
#         warnings.warn('No audio files found.')
#         n_participants = int(input('Enter number of participants: '))

#     # get the date of the experiment
#     date = os.path.basename(data_path).split('_')[0]
#     # get the experiment number
#     exp_num = os.path.basename(data_path).split('_')[1]
#     # get the survey data
#     survey_data, privacy_elections = get_survey_data(n_participants=n_participants, date=date, exp_num=exp_num)
#     # make the survey folder
#     survey_path = data_path / 'survey'
#     os.makedirs(survey_path, exist_ok=True)

#     for part, survey in survey_data.items():
#         survey['pre'].to_csv(survey_path / f'{part}_pre.csv', index=False)
#         survey['post'].to_csv(survey_path / f'{part}_post.csv', index=False)
#         print(f'Participant {part} pre-survey: {survey["pre"].shape[0]} items')
#         print(f'Participant {part} post-survey: {survey["post"].shape[0]} items')

#     privacy_elections.to_csv(survey_path / 'privacy_elections.csv', index=False)



#     print('Survey data saved to data folder\n')
#     print('##########################\n')
#     print('Data pull complete!\n')

#     return data_path

# TODO: Shift these last two qualtrics functions back to the qualtrics script itself. 
#       Refactor the qualtrics script so that only one api call is made per survey




