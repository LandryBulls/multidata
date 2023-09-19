#!/usr/bin/env python
# coding: utf-8


import os
from glob import glob
from pathlib import Path
import shutil
import sys
import time
from io import BytesIO
from tqdm import tqdm
import warnings
from qualtrics.pull_qualtrics import get_survey_data

today = time.strftime('%Y-%m-%d')
def transfer_file(source, dest_path):
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
    all_files = []
    for root, dirs, files in os.walk(card_path):
        for file in files:
            if '.Trash' not in root:
                all_files.append(os.path.join(root, file))
    return all_files

# get paths of SD cards connected
def get_sd_cards():
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
    cam_id = 0
    for card in connected_sd_cards:
        if any(['.360' in file for file in get_all_files(card)]):
            files = [file for file in get_all_files(card) if '.360' in file]
            card_id['360cam'] = {'card_path': str(card), 'files': files}
        elif any(['.mp4' in file.lower() for file in get_all_files(card)]):
            cam_id+=1
            files = [file for file in get_all_files(card) if '.mp4' in file.lower()]
            card_id[f'cam{cam_id}'] = {'card_path': str(card), 'files': files}
        elif any(['TRACK' in file for file in get_all_files(card)]):
            # TO DO: make sure audio files recorded on same date as video files
            files = [file for file in get_all_files(str(card)) if 'TRACK' in file]
            card_id['audio'] = {'card_path': card, 'files': files}
        else:
            print(f'Unknown card: {card} contains the following files:')
            print(get_all_files(card))

    assert len(card_id) == 4, f'Not all cards are connected\n Connected cards: {card_id.keys()}'

    return card_id

# func for getting the creation date of a file
def get_creation_date(path_to_file):
    return time.strftime('%Y-%m-%d', time.gmtime(os.path.getctime(path_to_file)))

# make sure all files have the same creation date and print the files for each unique date detected
def check_dates(card_id):
    dates = []
    for card in card_id:
        for file in card_id[card]['files']:
            dates.append(get_creation_date(file))
    dates = list(set(dates))
    if len(dates) != 1:
        warnings.warn(f'Files on {card} were not all created on the same date')
    else:
        date = dates[0]
        if date != today:
            warnings.warn(f'Files on {card} were created on {date} instead of {today} (today)')
        elif date == today:
            print(f'All files on were created today ({date})')

def get_exp_of_day():
    # get all experiments of the day
    today = time.strftime('%Y-%m-%d')
    data_path = Path('/safestore/users/landry/SCRAP/data/conversations_unconstrained')
    existing_data_folders = [exp for exp in glob(f'{data_path}/{today}*') if os.path.isdir(exp)]
    # get the number of the last experiment of the day
    if len(existing_data_folders) == 0:
        exp_num = 0
    else:
        # get the number of the last experiment of the day
        exp_num = f'{len(existing_data_folders):03d}'

    return f'{len(exp_num):03d}'

exp_num = get_exp_of_day()

def delete_card(card_path):
    os.chmod(card_path, 0o777)
    shutil.rmtree(card_path)

def run_transfer():
    card_id = get_sd_cards()
    # get number of participants based on number of microphone tracks
    n_participants = len(card_id['audio']['files'])

    print(f'Found {n_participants} participants')

    # make sure all files have the same creation date
    check_dates(card_id)

    # make an RA account for this
    data_path = Path('/safestore/users/landry/SCRAP/data/conversations_unconstrained') / f'{today}_{exp_num}'
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
        os.mkdir(data_path)
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

        print('##########################\n')
        print('Pulling survey data from Qualtrics...\n')
        survey_data = get_survey_data(n_participants=n_participants, date=today, exp_num=get_exp_of_day())
        print('Survey data pulled from Qualtrics\n')

        for part, survey in survey_data.items():
            pre, post = survey['pre'], survey['post']
            print(f'Participant {part} pre-survey: {pre.shape[0]} items\n')
            print(f'Participant {part} post-survey: {post.shape[0]} items\n')

        for part, survey in survey_data.items():
            survey['pre'].to_csv(data_path / f'{part}_pre.csv', index=False)
            survey['post'].to_csv(data_path / f'{part}_post.csv', index=False)

        print('Survey data saved to data folder\n')
        print('##########################\n')
        print('Data pull complete!\n')

        #
        # delete_approved = input('Delete files from SD cards? (y/n): ')
        # if delete_approved.lower() == 'y':
        #     for card in card_id:
        #         delete_card(card)
        #     print('Files deleted from SD cards')
        # else:
        #     print('SD card file deletion aborted. Files still on SD cards.')

    return data_path



