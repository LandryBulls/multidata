#!/usr/bin/env python

"""
This script contains functions for pulling data from Qualtrics. It is intended to be used in conjunction with the
data_management/file_transfer.py script.

It assumes that a file called qualtrics_credentials.txt exists in the qualtrics directory. This file should contain
the following information, in order, on separate lines:
    1. Qualtrics API token
    2. Qualtrics data center
    3. Qualtrics directory ID

It also assumes that a file called survey_ids.txt exists in the qualtrics directory. This file should contain the
following information, in order, on separate lines:
    1. Pre-survey ID for 4-person experiment
    2. Post-survey ID for 4-person experiment
    3. Pre-survey ID for 3-person experiment
    4. Post-survey ID for 3-person experiment
    5. Pre-survey ID for 2-person experiment
    6. Post-survey ID for 2-person experiment
    7. Payment election survey ID
"""

import pandas as pd
from IPython.core.display_functions import display
from QualtricsAPI.Setup import Credentials
from QualtricsAPI.Survey import Responses
import os

path_to_qualtrics_credentials = os.path.abspath(os.path.join(os.path.dirname(__file__), '../qualtrics_credentials.txt'))
path_to_survey_ids = os.path.abspath(os.path.join(os.path.dirname(__file__), '../survey_ids.txt'))

with open(path_to_qualtrics_credentials,'r') as f:
    credentials = f.read().splitlines()
    
with open(path_to_survey_ids,'r') as f:
    survey_ids = f.read().splitlines()

token = credentials[0].split(' ')[1]
data_center = credentials[1].split(' ')[1]
directory_id = credentials[2].split(' ')[1]

Credentials().qualtrics_api_credentials(token=token, data_center=data_center, directory_id=directory_id)

pre_4 = survey_ids[0].split(' ')[1]
post_4 = survey_ids[1].split(' ')[1]
pre_3 = survey_ids[2].split(' ')[1]
post_3 = survey_ids[3].split(' ')[1]
pre_2 = survey_ids[4].split(' ')[1]
post_2 = survey_ids[5].split(' ')[1]
payment_surv = survey_ids[6].split(' ')[1]

surveys = [pre_4, post_4, pre_3, post_3, pre_2, post_2, payment_surv]

letters = ['A', 'B', 'C', 'D']


def get_privacy_elections(post_data):
    """
    Takes the post-survey data and returns a dataframe containing the privacy elections for each participant.
    :param post_data:
    :type post_data:
    :return:
    :rtype:
    """
    # get privacy elections
    privacy_elections = post_data[['Q7', 'Q50', 'Q51', 'Q52']].rename(
        columns={'Q7': 'ID', 'Q50': 'beh', 'Q51': 'AV_general', 'Q52': 'AV_partial'})

    beh_full = 'and share de-identified data'
    beh_partial = 'but do not share'
    beh_del = 'Delete'
    av_full = 'share identifiable data'
    av_deriv = 'share de-identified derivative data'
    av_no_share = 'but do not share'
    av_del = 'Delete'

    privacy_elections['beh'] = privacy_elections['beh'].str.replace(f'^.*{beh_full}.*$', 'full', regex=True)
    privacy_elections['beh'] = privacy_elections['beh'].str.replace(f'^.*{beh_partial}.*$', 'use_noshare', regex=True)
    privacy_elections['beh'] = privacy_elections['beh'].str.replace(f'^.*{beh_del}.*$', 'delete', regex=True)
    privacy_elections['AV_general'] = privacy_elections['AV_general'].str.replace(f'^.*{av_full}.*$', 'full',
                                                                                  regex=True)
    privacy_elections['AV_general'] = privacy_elections['AV_general'].str.replace(f'^.*{av_deriv}.*$',
                                                                                  'share_derivative_only', regex=True)
    privacy_elections['AV_general'] = privacy_elections['AV_general'].str.replace(f'^.*{av_no_share}.*$', 'use_noshare',
                                                                                  regex=True)
    privacy_elections['AV_general'] = privacy_elections['AV_general'].str.replace(f'^.*{av_del}.*$', 'delete',
                                                                                  regex=True)

    return privacy_elections

def get_survey_data(n_participants, date, exp_num):
    """
    Grabs the survey data for a given experiment from Qualtrics.
    :param n_participants: Number of participants in the experiment
    :type n_participants: int
    :param date: The date the experiment was run
    :type date: datetime string formatted as YYYY-MM-DD
    :param exp_num: The experiment number, determined by n of the day.
    :type exp_num: 3d int
    :return: A dictionary containing the survey data for each participant. Survey data is separated into pre and post conversation.
    :rtype: dict
    """

    if n_participants==4:
        pre = pre_4
        post = post_4
    elif n_participants==3:
        pre = pre_3
        post = post_3
    elif n_participants==2:
        pre = pre_2
        post = post_2
    else:
        print('Invalid number of participants')
        return None
    
    pre_data = Responses().get_survey_responses(survey=pre)
    post_data = Responses().get_survey_responses(survey=post)
    payment = Responses().get_survey_responses(survey=payment_surv)
    
    # grab rows with the correct date and exp_num
    pre_data = pre_data[(pre_data['StartDate'].str.contains(date)) & (pre_data['Q13'].str.contains(exp_num))]
    post_data = post_data[(post_data['StartDate'].str.contains(date)) & (post_data['Q13'].str.contains(exp_num))]

    # organize payment info into a dataframe and pull
    payment_elections = payment[(payment['StartDate'].str.contains(date))]
    payment_elections = payment_elections[['Q1', 'Q3', 'Q4', 'Q5']]
    pay_df = pd.DataFrame(columns=['name', 'email', 'netID', 'election'])

    # get privacy elections
    privacy_elections = get_privacy_elections(post_data)
    print('#############################\n')
    print('Privacy elections:\n')
    display(privacy_elections)

    print('#############################\n')
    print('Payment elections:\n')
    for i in range(payment_elections.shape[0]):
        to_add = payment_elections.iloc[i].values
        if to_add[-1]=='1':
            to_add[-1] = 'T-points'
        elif to_add[-1]=='2':
            to_add[-1] = 'cash'
        pay_df.loc[i] = payment_elections.iloc[i].values

    # just printing it out for now until I can get dropbox integration
    display(pay_df)
    print('\n#############################\n')





    # get the netIDs of the participants




    letters_sub = letters[:n_participants]
    participant_data = dict(zip(letters_sub, [None]*n_participants))
    
    for letter in letters_sub:
        participant_pre_data = pre_data[pre_data['Q7']==letter]
        participant_post_data = post_data[post_data['Q7']==letter]
        participant_data[letter] = {'pre':participant_pre_data, 'post':participant_post_data}
        
    return participant_data, privacy_elections

def get_payments():
    payment = Responses().get_survey_responses(survey=payment_surv)
    return payment





