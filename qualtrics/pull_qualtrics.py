#!/usr/bin/env python

from QualtricsAPI.Setup import Credentials
from QualtricsAPI.Survey import Responses

with open('../qualtrics_credentials.txt','r') as f:
    credentials = f.read().splitlines()
    
with open('../survey_ids.txt','r') as f:
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

surveys = [pre_4,post_4,pre_3,post_3,pre_2,post_2]

letters = ['A', 'B', 'C', 'D']

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
    
    # grab rows with the correct date and exp_num
    pre_data = pre_data[(pre_data['StartDate'].str.contains(date)) & (pre_data['Q13']==exp_num)]
    post_data = post_data[(post_data['StartDate'].str.contains(date)) & (post_data['Q13']==exp_num)]
    
    letters = letters[:n_participants]
    participant_data = dict(zip(letters, [None]*n_participants))
    
    for letter in letters:
        participant_pre_data = pre_data[pre_data['Q7']==letter]
        participant_post_data = post_data[post_data['Q7']==letter]
        participant_data[letter] = {'pre':participant_pre_data, 'post':participant_post_data}
        
    return participant_data


