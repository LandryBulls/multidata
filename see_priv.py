from pathlib import Path
import pandas as pd
from tqdm import tqdm

main_data_dir = '/safestore/users/landry/SCRAP/data/andromeda_storage/conversations_unconstrained'


def add_priv(data_dir):
    data_dir = Path(data_dir)
    survey_dir = data_dir / 'survey'
    post_surveys = [str(i) for i in survey_dir.glob('*post*.csv')]
    if len(post_surveys) == 0:
        print(f'No post surveys found in {data_dir}')
    else:
        all_surveys = [pd.read_csv(i) for i in post_surveys]
        all_surveys = pd.concat(all_surveys)
        all_surveys = all_surveys[['Q7', 'Q50', 'Q51', 'Q52']]
        all_surveys.to_csv(data_dir / 'privacy_elections.csv', index=False)

alldirs = [i for i in Path(main_data_dir).iterdir() if Path(i).is_dir()]
alldirs = [i for i in alldirs if not (i / 'privacy_elections.csv').exists()]

for d in tqdm(alldirs):
    add_priv(d)
