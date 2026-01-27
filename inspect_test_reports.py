"""A simple helper to display the latest N (default 10) Test reports of a test

Usage:
inspect_test_reports.py test_name number_of_tests

"""
import sys

import json

from configuration import CONFIG
from utilities.test_utilities import display_report_from_json


def inspect_test_reports(test_name: str, number_of_tests: int):
    path = f"{CONFIG['folders']['test_reports']}/{test_name}{'.jsonl' if not test_name.endswith('.jsonl') else ''}"
    with open(path, 'r') as f:
        lines = f.readlines()
        last_n_lines = lines[-number_of_tests:]
        for line in last_n_lines:
            json_data = json.loads(line)
            print(display_report_from_json(json_data))



if __name__ == '__main__':
    test_name = sys.argv[1]
    number_of_tests = int(sys.argv[2]) if len(sys.argv) == 2 else 10
    inspect_test_reports(test_name, number_of_tests)


