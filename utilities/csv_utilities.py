"""Utilities (classes, functions) for tests on CSV data (files and APIs).

"""

import csv
import io
import requests
from contextlib import contextmanager
import re

from utilities.file_and_path_utilities import get_path
from utilities.string_utilities import strip_html_tags
from utilities.test_utilities import DataTest


def load_csv_from_url(url: str, data_test = None, delimiter =';', quotechar ='"', key: str = None, silent=False):
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
    if response.status_code < 400:
        if not silent:
            data_test.log_info(message)
    else:
        data_test.log_failure(message)
        return [], [], size, data_test

    encoding = 'utf-8-sig' if response.content.startswith(b'\xef\xbb\xbf') else 'utf-8'

    csv_data = io.StringIO(response.content.decode(encoding))
    csv_reader = csv.reader(csv_data, delimiter=delimiter, quotechar=quotechar)
    header = next(csv_reader)
    data_rows = list(csv_reader)
    return header, data_rows, response.status_code, data_test


def load_csv_from_file(relative_path: str, delimiter=';') -> list[list]:
    """Load a CSV file from the given relative path, respective the project root directory; returns None if failed."""
    try:
        with open(get_path(relative_path), newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=delimiter)
            data = [row for row in reader]
        return data
    except Exception:
        return None


def strip_quotes(value: str, quotechar: str) -> str:
    return value[1:-1] if value.startswith(quotechar) and value.endswith(quotechar) else value


def load_csv_streaming_and_do_data_checks(url: str, column_headers: list = None, column_re_matches: list = None,
                                          delimiter: str = ';', quotechar: str = '"',
                                          data_test: DataTest = None, line_count_range: tuple = None,
                                          skip_logging_after = 100) -> DataTest:
    """Load a CSV file at the given URL, using a stream-based approach (not loading in memory) and do some data checks on it.

    :param url: - URL from which to load the CSV
    :param column_headers: - list of header names which must be present in the CSV's first row.
    :param column_re_matches: - regexp expressions that the given column must match
    :param delimiter: - the CSV delimiter to use (';' by default)
    :param quotechar: - the CSV quotechar to use ('"' by default)
    :param data_test: - a DataTest object where to report test findings.
    :param line_count_range: - range (min, max) of lines the CSV should have.
    :param skip_logging_after: - skip collecting log messages after this number of log messages.
    :return: data_test - the DataTest object containing the test findings.
    """
    if data_test is None:
        data_test = DataTest(name="load_csv_streaming_and_do_data_checks", skip_logging_after=skip_logging_after)

    if column_headers is not None:
        column_headers = [strip_quotes(v, quotechar) for v in column_headers]
    with https_lines_iterator(url, encoding="utf-8", skip_empty=True) as lines:
        for i_line, line in enumerate(lines):
            fields_in_row = [strip_quotes(v, quotechar) for v in line.split(delimiter)]
            if column_headers is not None:
                if len(column_headers) != len(fields_in_row):
                    data_test.log_failure(f"Row {i} has cell count {len(fields_in_row)} not matching {len(column_headers)} column headers!")
            if i_line == 0:
                if column_headers is not None:
                    non_matches = ""
                    for i_col, column_header in enumerate(column_headers):
                        if column_header != fields_in_row[i_col]:
                            non_matches += f"col. {i_col}: {column_header}!={fields_in_row[i_col]}, "
                    if non_matches != "":
                        data_test.log_failure(f"Column headers not as expected: {non_matches[:-2]}!")
            else:
                if column_re_matches is not None:
                    non_matches = ""
                    for i_col, column_re_match in enumerate(column_re_matches):
                        if (i_col < len(fields_in_row)) and not re.match(column_re_match, fields_in_row[i_col]):
                            non_matches += f"col. {i_col}: {fields_in_row[i_col]} not matching '{column_re_match}', "
                    if non_matches != "":
                        data_test.log_failure(f"Row fields regex patterns not as expected: {non_matches[:-2]}!")

    if line_count_range is not None:
        if not(line_count_range[0] <= i_line <= line_count_range[1]):
            data_test.log_failure(f"CSV has {i_line} lines, not in range {line_count_range}!")

    data_test.log_info(f"Loaded and checked {i_line} lines / {len(column_headers)} columns of CSV data.")

    return data_test




_UTF8_BOM = b"\xef\xbb\xbf"

@contextmanager
def https_lines_iterator(url: str, *, timeout: tuple[float, float] = (5.0, 30.0),
    headers: dict = None, chunk_size: int = 8192,
    encoding: str = None,   # e.g., "utf-8" to yield str; None yields bytes
    errors: str = "strict",        # decoding error handling if encoding is set
    skip_empty: bool = False,      # skip blank lines (b"" / "")
    strip_bom: bool = True,        # remove UTF-8 BOM from first line
):
    """Context-managed iterator over an HTTPS line-based resource.
    - Yields bytes by default (no Unicode decoding).
    - If 'encoding' is set (e.g., "utf-8"), lines are decoded to str.
    - Lines are yielded without trailing newline characters (as per requests.iter_lines).
    """
    with requests.get(url, stream=True, headers=headers, timeout=timeout) as resp:
        resp.raise_for_status()

        # iter_lines handles line boundaries across chunks; returns bytes here
        source_iter = resp.iter_lines(decode_unicode=False, chunk_size=chunk_size)

        def _gen():
            first = True
            for line in source_iter:
                if (line is None) or (skip_empty and line == b""):
                    continue
                if first and strip_bom:
                    if line.startswith(_UTF8_BOM):  # Remove UTF-8 BOM if present
                        line = line[len(_UTF8_BOM):]
                    first = False
                elif first:
                    first = False
                if encoding is None:
                    yield line  # bytes
                else:
                    yield line.decode(encoding, errors)  # str

        yield _gen()
