# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Model implementation
"""

import json
from pathlib import Path
import logging as log
from typing import Dict
from scr.logic.errors import ModelError

_EXTENSION = '.json'


def save(data: Dict, name: str, folder: str ='', home_path: str = Path.home()) -> None:
    fp = Path(home_path, folder)
    log.debug(f"Saving information in the file: {fp}")
    while True:
        if fp.exists():
            break
        else:
            user_input = input("This folder doesn't exist. Do you want create it? [yes]/no: ")
            log.warning(f"This folder doesn't exist. Do you want create it? [yes]/no: {user_input}")
            if _user_decision(user_input):
                fp.mkdir()
                log.debug(f"{folder} folder created.")
                break
            else:
                folder = input("Write new name: ")
                log.debug(f"The new folder is: {folder}.")
                fp = Path(home_path, folder)

    file_name = name + _EXTENSION
    fp = Path(home_path, folder, file_name)
    log.debug(f"Saving information in the file: {file_name}")
    while True:
        if fp.exists():
            if fp.is_dir():
                log.warning(f"{fp} is a folder, not a file!")
                _user_decision('yes')
            else:
                user_input = input(f"{name} file already exists. Do you want rename it? [yes]/no: ")
            if _user_decision(user_input):
                name = input("Write new file name: ")
                log.debug(f"The new file name is: {name}.")
                fp = Path(home_path, folder, name + _EXTENSION)
            else:
                break
        else:
            break

    log.info(f"File saving in: {fp}.")
    # Save
    fp = fp.open('w')
    json.dump(data, fp, indent=4, ensure_ascii=False, sort_keys=True)
    fp.close()
    log.info("File saved successfully!")


def load(name: str, folder: str ='', home_path: str =Path.home()):
    """
    :raise ModelError: if data can't be loaded.
    """
    # Check home_path
    fp = Path(home_path, folder, name + _EXTENSION)
    log.debug(f"Loading file: {fp}")
    if fp.exists() and fp.is_file():
        # load
        fp = fp.open('r')
        data_loaded = json.load(fp)
        fp.close()
        log.info(f"File {fp} loaded successfully.")
        return data_loaded
    else:
        fp_dir = Path(home_path, folder, name)
        if fp.exists():
            msg = f"{fp_dir} is an invalid path."
            log.error(msg)
        elif fp_dir.is_dir():
            msg = f"{fp_dir} is a folder, not a file!"
            log.error(msg)
        else:
            msg = f"{fp_dir} file doesn't exist."
            log.error(msg)
        raise ModelError(msg)


def _user_decision(answer, default_answer='yes'):
    log.warning(f"User decision: {answer}.")
    if answer is '':
        answer = default_answer
        log.warning(f"User select the default answer: {default_answer}.")
    if answer == 'yes':
        return True
    elif answer == 'no':
        return False
    else:
        print("Invalid answer.")
        log.warning("Invalid answer, user repeat the answer.")
        answer = input('Please repeat the answer:')
        return _user_decision(answer, default_answer)
