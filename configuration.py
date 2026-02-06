"""Basic configuration file for overall, general configuration, including secrets.

In a local setup, this file may be complemented with a file named local_configuration.py file,
which supersedes some or all of the CONFIG values, especially secrets, etc.

If a test wants to import this configuriation.py, it may read CONFIG values then using get_prop(...).
However, the test_runner.py will pass the whole CONFIG dict to each test anyway.

NOTE ⚠: local_configuration.py MUST NOT BE COMMITTED to github.

"""

import os

# a generic dict for properties as key-value pairs.
# test_runner.py passes a deep copy of this to the "config" parameter in the run() function of the test.
CONFIG = {
    "folders": {
        "test_reports": "data/test_reports",
        "persistent_test_data": "data/persistent_test_data",
        "html": "data/html",
        "logs": "data/logs",
        "templates": "templates",
        "tests": "tests"
    }
}


def get_prop(key):
    """Returns the property value for the given key in the CONFIG dict in configuration.py / local_configuration.py; returns None if key is not defined."""
    return CONFIG.get(key)


# ensure that the folders and subfolders exist; create them if not:
for folder_path in CONFIG["folders"].values():
    os.makedirs(os.path.abspath(folder_path), exist_ok=True)


# if there exists a local_configuration, it is used and may supersede some of the above constants.
try:
    from local_configuration import *
except:
    pass