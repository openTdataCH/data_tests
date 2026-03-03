"""Utilities (classes, functions) for tests on JSON data (files and APIs).

"""

import json
import requests
import time

from utilities.file_and_path_utilities import get_path
from utilities.string_utilities import strip_html_tags
from utilities.test_utilities import DataTest

def load_json(url: str, data_test=None, key: str = None, json_schema=None) -> (dict, int, object):
    """Load a JSON file from an URL (permalink); returns the data (dict), size (int) and test report, as a tuple."""
    if data_test is None:
        data_test = DataTest(name="load_json")
    headers = {}
    if key is not None:
        headers["Authorization"] = f"{key}"

    max_retries = 3
    response = None
    raw_content = b""

    for attempt in range(max_retries):
        try:
            temp_response = requests.get(url, headers=headers, timeout=15)

            temp_response.raise_for_status()
            raw_content = temp_response.content
            response = temp_response
            break

        except (requests.exceptions.RequestException,
                requests.exceptions.ChunkedEncodingError) as e:
            if attempt < max_retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue

            error_msg = f"Network failure after {max_retries} attempts: {url} - Error: {str(e)}"
            print(error_msg)
            data_test.log_exception(error_msg)
            return {}, 0, data_test

    if response is None or not raw_content:
        return {}, 0, data_test

    size = len(raw_content)
    try:
        decoded_str = raw_content.decode('utf-8', errors='replace')
        excerpt = strip_html_tags(decoded_str)[0:200]
    except Exception:
        excerpt = "Could not decode content"

    message = f"Response {response.status_code} with {size} bytes, excerpt: {excerpt}..."

    is_lt_400 = data_test.test(response.status_code < 400, if_false_log_failure=message)
    if not is_lt_400:
        return {}, size, data_test

    try:
        json_data = json.loads(raw_content)
        return json_data, size, data_test
    except json.JSONDecodeError as e:
        error_msg = f"JSON Decode Error at {url}: {str(e)}"
        data_test.log_warning(error_msg)
        return {}, size, data_test

def load_json_file(relative_path: str):
    """Load a JSON file from the given relative path, respective the project root directory; returns None if failed."""
    try:
        with open(get_path(relative_path), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_json_file(relative_path: str, data: dict):
    with open(get_path(relative_path), "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2))


