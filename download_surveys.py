#!/usr/bin/env python
"""
Download all Qualtrics survey responses to CSV files.

Usage:
    conda activate fusion
    python download_surveys.py

Outputs CSV files to:
    /safestore/users/landry/SCRAP/data/andromeda_storage/conversations_unconstrained/surveys/

Options:
    - useLabels=False: Returns numeric values (1-5) instead of text labels ("Agree a little")
    - breakoutSets: Multi-value questions get separate columns per value
"""

import io
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

# Paths
SCRIPT_DIR = Path(__file__).parent
CREDENTIALS_PATH = SCRIPT_DIR / 'qualtrics_credentials.txt'
SURVEY_IDS_PATH = SCRIPT_DIR / 'survey_ids.txt'
OUTPUT_DIR = Path('/safestore/users/landry/SCRAP/data/andromeda_storage/conversations_unconstrained/surveys')


def load_credentials():
    """Load Qualtrics API credentials."""
    with open(CREDENTIALS_PATH, 'r') as f:
        lines = f.read().splitlines()
    token = lines[0].split(' ')[1]
    data_center = lines[1].split(' ')[1]
    return token, data_center


def load_survey_ids():
    """Load survey IDs and return as dict."""
    with open(SURVEY_IDS_PATH, 'r') as f:
        lines = f.read().splitlines()
    
    surveys = {}
    for line in lines:
        if line.strip():
            parts = line.split(' ')
            if len(parts) >= 2:
                name, survey_id = parts[0], parts[1]
                surveys[name] = survey_id
    return surveys


def download_survey(survey_id, token, data_center):
    """
    Download survey using Qualtrics API directly with:
    - useLabels: Question text as column labels
    - breakoutSets: Multi-value questions split into separate columns
    """
    base_url = f"https://{data_center}.qualtrics.com/API/v3/surveys/{survey_id}/export-responses"
    headers = {
        "X-API-TOKEN": token,
        "Content-Type": "application/json"
    }
    
    # Start export with desired parameters
    # useLabels=False returns numeric values (1-5) instead of text ("Agree a little")
    # breakoutSets=True splits multi-value questions into separate columns
    export_params = {
        "format": "csv",
        "useLabels": False,
        "breakoutSets": True
    }
    
    # Step 1: Start the export
    response = requests.post(base_url, json=export_params, headers=headers)
    response.raise_for_status()
    progress_id = response.json()["result"]["progressId"]
    
    # Step 2: Poll for completion
    progress_url = f"{base_url}/{progress_id}"
    while True:
        response = requests.get(progress_url, headers=headers)
        response.raise_for_status()
        result = response.json()["result"]
        
        if result["status"] == "complete":
            file_id = result["fileId"]
            break
        elif result["status"] == "failed":
            raise Exception(f"Export failed for survey {survey_id}")
        
        time.sleep(1)
    
    # Step 3: Download the file
    file_url = f"{base_url}/{file_id}/file"
    response = requests.get(file_url, headers=headers)
    response.raise_for_status()
    
    # Extract CSV from zip
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        csv_name = z.namelist()[0]
        with z.open(csv_name) as f:
            df = pd.read_csv(f)
    
    return df


def main():
    # Load credentials
    token, data_center = load_credentials()
    
    # Load survey IDs
    surveys = load_survey_ids()
    print(f"Found {len(surveys)} surveys to download:\n")
    for name, sid in surveys.items():
        print(f"  {name}: {sid}")
    print()
    
    # Create output directory if needed
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download each survey
    for name, survey_id in surveys.items():
        output_path = OUTPUT_DIR / f"{name}.csv"
        try:
            print(f"  Downloading {name}...")
            df = download_survey(survey_id, token, data_center)
            df.to_csv(output_path, index=False)
            print(f"  Saved to {output_path} ({len(df)} responses)")
        except Exception as e:
            print(f"  ERROR downloading {name}: {e}")
    
    print(f"\nAll surveys saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
