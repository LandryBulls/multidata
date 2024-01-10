from pathlib import Path
import pandas as pd

dirpath = '/safestore/users/landry/SCRAP/packages/multidata/data_dir.txt'
with open(dirpath, 'r') as f:
    main_data_dir = f.readline().strip()

def add_priv(data_dir):
    data_dir = Path(data_dir)
    survey_dir = data_dir / 'survey'
    post_surveys = [str(i) for i in survey_dir.glob('*post*.csv')]
    all_surveys = [pd.read_csv(i) for i in post_surveys]
    all_surveys = pd.concat(all_surveys)
    all_surveys = all_surveys[['Q7', 'Q50', 'Q51', 'Q52']]
    all_surveys.to_csv(data_dir / 'privacy_elections.csv', index=False)

alldirs = [str(i) for i in Path(main_data_dir).iterdir() if Path(i).is_dir()]

for dir in alldirs:
    add_priv(dir)

