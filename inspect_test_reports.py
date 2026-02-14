"""A simple helper to display test reports.
- test_name: (part of) the name of the test
- the time range (ISO8601 date-time) of the test

Example isage: show logs for "...my_test..." at 18:.. hours on Feb. 11:
inspect_test_reports.py my_test 2026-02-11T18


"""
import sys

import json
import os
from configuration import CONFIG
from utilities.test_utilities import display_report_from_json
from datetime import datetime as dt

def _print_header(title: str, line_char = '=', line_length = 80):
    line = line_char * line_length
    print(f"{line}\n{title}\n{line}")


def inspect_test_reports(test_name: str, timestamp_iso8601: str):
    tr_dir = CONFIG['folders']['test_reports']
    reports = [f[:-6] for f in os.listdir(tr_dir) if test_name.lower() in f.lower() and f.endswith('.jsonl')]
    for tr in reports:
        jsonl_file_path = f"{tr_dir}/{tr}.jsonl"
        _print_header(f"TEST REPORTS FOR {tr} AT {timestamp_iso8601}")

        with open(jsonl_file_path, 'r') as f:
            for line in f.readlines():
                if line.strip().startswith('{'):
                    json_data = json.loads(line)
                    if timestamp_iso8601 in json_data['logs'][:100]:
                        print(display_report_from_json(json_data))


if __name__ == '__main__':
    test_name = sys.argv[1] if len(sys.argv) > 1 else ""
    timestamp_iso8601 = int(sys.argv[2]) if len(sys.argv) > 2 else dt.now().isoformat()[:13]
    _print_header(f"INSPECT TEST REPORTS CONTAINING '{test_name}' AT DATE/TIME '{timestamp_iso8601}'")
    inspect_test_reports(test_name, timestamp_iso8601)
