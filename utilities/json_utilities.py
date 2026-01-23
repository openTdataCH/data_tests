"""Utilities (classes, functions) for tests on JSON data (files and APIs).

"""

import json
import requests

from utilities.file_and_path_utilities import get_path
from utilities.test_utilities import DataTest


def load_json(url: str, data_test = None, key: str = None, json_schema = None) -> (dict, int):
    """Load a JSON file from an URL (permalink); returns the data (dict), size (int) and test report, as a tuple."""
    if data_test is None:
        data_test = DataTest(name="load_json")
    data_test.log_info(f"Calling {url} now...")
    headers = {}
    if key is not None:
        headers["Authorization"] = f"Bearer {key}"

    response = requests.get(url, headers=headers)
    size = len(response.content)
    message = f"Response {response.status_code} with {len(response.content)} bytes, excerpt: {str(response.content)[0:200]}"
    is_lt_400 = data_test.test(response.status_code < 400, if_true_log_info=message, if_false_log_failure=message)
    if not is_lt_400:
        return {}, size, data_test

    # if json_schema is not None: TODO implement schema test

    return json.loads(response.content.decode('utf-8')), size, data_test


def load_json_file(relative_path: str):
    """Load a CSV file from the given relative path, respective the project root directory; returns None if failed."""
    try:
        with open(get_path(relative_path), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_json_file(relative_path: str, data: dict):
    with open(get_path(relative_path), "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2))


