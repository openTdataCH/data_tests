"""A simple test demo example which has no dependencies.

The test does these checks:
- load a resource from opentransportdata.swiss
- do a simple size check
- generate the Test Report as a JSON and return it.

In this case, the program logic has to do the counting and logging by itself.

The run method requires no config at all (hence, no 'config' parameter).
"""
import io
import requests
import csv

def run() -> dict:
    test_report = {'name': 'simple_independent_test', 'n_warnings': 0, 'n_failures': 0, 'n_exceptions': 0, 'exceptions': [], "logs": ""}

    response = requests.get("https://data.opentransportdata.swiss/dataset/atzgf/resource_permalink/gf-datei-2025.csv")

    if response.status_code >= 400:
        test_report['n_failures'] += 1
        test_report['logs'] += f"Dataset load fails with status code {response.status_code}!"
        return test_report

    with io.BytesIO(response.content) as csv_file:
        reader = csv.reader(io.TextIOWrapper(csv_file, encoding='utf-8'))
        header = next(reader)
        rows = [row for row in reader]

    # example of a test which reports a "failure" if condition not ok:
    if "DayType" in header and "TrainNumber" in header:
        test_report['logs'] = test_report['logs'] + f"info:   Header fields are ok.\n"
    else:
        test_report['logs'] = test_report['logs'] + f"FAILURE: Header fields {str(header)} are not ok!\n"
        test_report['n_failures'] += 1

    # example of a test which reports a warning if condition not ok:
    if 34 < len(rows) < 38:
        test_report['logs'] = test_report['logs'] + f"info:    Row count is ok, len(rows)={len(rows)}.\n"
    else:
        test_report['logs'] = test_report['logs'] + f"WARNING: Rows are not as expected, len(rows)={len(rows)}!\n"
        test_report['n_warnings'] += 1

    # add some extra example messages directly:
    test_report['logs'] = test_report['logs'] + "info:     An extra example info message.\n"

    test_report['logs'] = test_report['logs'] + f"WARNING: An extra example warning message.\n"
    test_report['n_warnings'] += 1

    test_report['logs'] = test_report['logs'] + f"FAILURE: An extra example failure message..\n"
    test_report['n_failures'] += 1

    test_report['logs'] = test_report['logs'] + f"EXCEPTION: An extra example excpetion message..\n"
    test_report['n_exceptions'] += 1
    test_report['exceptions'].append(ValueError("Example ValueError"))

    # at the end, return the data_test object, it contains the logs and the counts (warnings, failures, etc.):
    return test_report


if __name__ == '__main__':
    tr = run()
    print(tr)
