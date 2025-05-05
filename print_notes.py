from pathlib import Path

main_dir = Path('/safestore/users/landry/SCRAP/data/andromeda_storage/conversations_unconstrained')

for i in main_dir.iterdir():
    if i.is_dir():
        print(i.name)
        for j in i.iterdir():
            if j.is_file() and 'NOTE' in j.name and not j.name.startswith('.'):
                print(j.name)
                with open(j, 'r') as f:
                    print(f.read())
                print('\n\n')