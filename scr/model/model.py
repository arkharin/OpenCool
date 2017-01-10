# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Model implementation
"""

import json
from pathlib import Path

_EXTENSION = '.json'


def save(data, file_name, folder='', home_path=Path.home()):
    fp = Path(home_path, folder)
    while True:
        if fp.exists():
            break
        else:
            user_input = input("This directory doesn't exist. Do you want create it? [yes]/no: ")
            if _user_decision(user_input):
                fp.mkdir()
                break
            else:
                folder = input('Write new name: ')
                fp = Path(home_path, folder)

    fp = Path(home_path, folder, file_name + _EXTENSION)
    while True:
        if fp.exists():
            user_input = input('This file already exists. Do you want rename it? [yes]/no: ')
            if _user_decision(user_input):
                name = input('Write new file name: ')
                fp = Path(home_path, folder, name)
            else:
                break
        else:
            break

    print('File saved in: ', fp)
    # Save
    fp = fp.open('w')
    json.dump(data, fp, indent=4, ensure_ascii=False, sort_keys=True)
    fp.close()
    print('Save successfully!')


def load(file_name, folder='', home_path=Path.home()):
    # Check home_path
    fp = Path(home_path, folder, file_name + _EXTENSION)
    if fp.exists() and fp.is_file():
        # load
        fp = fp.open('r')
        data_loaded = json.load(fp)
        fp.close()
        print(file_name, 'loaded successfully')
    else:
        fp_dir = Path(home_path, folder, file_name)
        if fp.exists():
            print('Invalid path')
        elif fp_dir.is_dir():
            print("It's a folder, not a file")
        else:
            print("This file doesn't exist")
        data_loaded = {}
        print('Empty data is loaded')
    return data_loaded


def _user_decision(answer, default_answer='yes'):
    if answer is '':
        answer = default_answer

    if answer == 'yes':
        return True
    elif answer == 'no':
        return False
    else:
        print('Invalid answer')
        answer = input('Please repeat the answer:')
        return _user_decision(answer, default_answer)
