"""Utilities (classes, functions) for tests on CSV data (files and APIs).

"""

import csv
import io
import requests

from utilities.file_and_path_utilities import get_path
from utilities.test_utilities import DataTest
from utilities.string_utilities import strip_html_tags


def load_csv_from_url(url: str, data_test = None, delimiter =';', quotechar ='"', key: str = None):
    """Load a CSV file from a URL (permalink); returns a header (list), data rows (list), size (int) nd test report, as a tuple."""
    if data_test is None:
        data_test = DataTest(name="load_csv")

    headers = {}
    if key is not None:
        headers["Authorization"] = f"Bearer {key}"

    response = requests.get(url, headers=headers)
    size = len(response.content)
    excerpt = strip_html_tags(response.content.decode('utf-8'))[0:50]
    message = f"Response {response.status_code}, {len(response.content)} bytes, excerpt: {excerpt}... for {url}"
    is_lt_400 = data_test.test(response.status_code < 400,
                               if_true_log_info=message,
                               if_false_log_failure=message)
    if not is_lt_400:
        return [], [], size, data_test

    encoding = 'utf-8-sig' if response.content.startswith(b'\xef\xbb\xbf') else 'utf-8'

    csv_data = io.StringIO(response.content.decode(encoding))
    csv_reader = csv.reader(csv_data, delimiter=delimiter, quotechar=quotechar)
    header = next(csv_reader)
    data_rows = list(csv_reader)
    return header, data_rows, response.status_code, data_test


def load_csv_from_file(relative_path: str) -> list[list]:
    """Load a CSV file from the given relative path, respective the project root directory; returns None if failed."""
    try:
        with open(get_path(relative_path), newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            data = [row for row in reader]
        return data
    except Exception:
        return None


