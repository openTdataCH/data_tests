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


def load_csv_from_file(relative_path: str, delimiter=';', encoding='utf-8') -> list[list]:
    """Load a CSV file from the given relative path, respective the project root directory; returns None if failed."""
    try:
        with open(get_path(relative_path), newline='', encoding=encoding) as csvfile:
            reader = csv.reader(csvfile, delimiter=delimiter)
            data = [row for row in reader]
        return data
    except Exception:
        return None


def strip_quotes(value: str, quotechar: str) -> str:
    return value[1:-1] if value.startswith(quotechar) and value.endswith(quotechar) else value


def load_csv_streaming_and_do_data_checks(url: str = None, stream = None, schema_config: dict = None,
                                          delimiter: str = ';', quotechar: str = '"',
                                          data_test: DataTest = None, filename: str = "CSV") -> DataTest:
    """Load a CSV file at the given URL, using a stream-based approach or loading in memory and do some data checks on it."""
    if data_test is None:
        data_test = DataTest(name="csv_schema_check")

    column_rules = schema_config.get("columns", {}) if schema_config else {}
    seen_values = {col: set() for col, rules in column_rules.items() if rules.get("unique")}
    i_line = 0

    if stream is not None:
        csv_reader = csv.reader(stream, delimiter=delimiter, quotechar=quotechar)
        i_line = _execute_validation(csv_reader, column_rules, seen_values, data_test, filename)
        data_test.log_info(f"filename = {filename}")
    elif url is not None:
        with https_lines_iterator(url, encoding="utf-8", skip_empty=True) as lines:
            csv_reader = csv.reader(lines, delimiter=delimiter, quotechar=quotechar)
            i_line = _execute_validation(csv_reader, column_rules, seen_values, data_test, filename)
            data_test.log_info(f"filename = {filename} from {url} checked")
    else:
        data_test.log_failure("Neither URL nor Stream handed over for validation.")
        return data_test

    if schema_config and "line_count_range" in schema_config:
        min_lines, max_lines = schema_config["line_count_range"]
        if not (min_lines <= i_line <= max_lines):
            data_test.log_failure(f"{filename} has a total of {i_line} lines. Expected range: [{min_lines}, {max_lines}].")

    return data_test

def _execute_validation(csv_reader, column_rules, seen_values, data_test, filename) -> int:
    """Internal support function for iteration through columns and rows"""
    i_line = 0
    try:
        headers = [h.strip() for h in next(csv_reader)]
        i_line += 1
        if column_rules:
            validate_headers(headers, column_rules, data_test, filename)
    except StopIteration:
        data_test.log_failure(f"{filename} is completely empty (no Header line).")
        return i_line

    for row in csv_reader:
        i_line += 1
        if len(row) != len(headers):
            data_test.log_failure(f"{filename}, Line {i_line} has {len(row)} entries, expected were {len(headers)}.")
            continue

        if column_rules:
            row_dict = dict(zip(headers, row))
            validate_row(row_dict, i_line, column_rules, seen_values, data_test, filename)

    return i_line




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


def validate_headers(actual_headers: list[str], column_rules: dict, data_test: DataTest, filename: str = "CSV"):
    """Checks the CSV header against the expected columns from the config."""
    if not column_rules:
        return

    expected_headers = list(column_rules.keys())

    missing_required = []
    for expected_h, rules in column_rules.items():
        if expected_h not in actual_headers:
            if rules.get("required", False):
                missing_required.append(expected_h)

    if missing_required:
        data_test.log_failure(f"{filename}: Missing mandatory columns: {missing_required}")

    unexpected = [h for h in actual_headers if h not in expected_headers]
    if unexpected:
        data_test.log_failure(f"{filename}: Unexpected (new) column found: {unexpected}")


def validate_row(row_dict: dict, row_num: int, column_rules: dict, seen_values: dict, data_test: DataTest, filename: str = "CSV"):
    """Validates the content of a single data row."""
    for col_name, rules in column_rules.items():
        if col_name not in row_dict:
            continue
        value = row_dict.get(col_name)

        # 1. Check: Required / empty values
        if value is None or value.strip() == "":
            if rules.get("required", False):
                data_test.log_failure(f"{filename}, Row {row_num}: Column '{col_name}' is empty, but a mandatory field.")
            continue

        # 2. Check: Regex matching
        if "regex" in rules:
            if not re.match(rules["regex"], value):
                data_test.log_failure(f"{filename}, Row {row_num}: '{value}' in Column '{col_name}' does not match Regex '{rules['regex']}'.")

        # 3. Check: Allowed Values (Enum)
        if "enum" in rules:
            if value not in rules["enum"]:
                data_test.log_failure(f"{filename}, Row {row_num}: '{value}' in Column '{col_name}' is not an allowed value from: {rules['enum']}.")

        # 4. Check: Uniqueness (Unique)
        if rules.get("unique", False):
            if value in seen_values[col_name]:
                data_test.log_failure(f"{filename}, Row {row_num}: Duplicate found in Unique column '{col_name}': '{value}'.")
            else:
                seen_values[col_name].add(value)