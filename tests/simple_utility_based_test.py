"""A simple test demo example which makes use of the utility function.

The test does these checks:
- load a resource from opentransportdata.swiss
- do a simple size check

The run method requires no config at all (hence, no 'config' parameter).
"""
from utilities.csv_utilities import load_csv_from_url
from utilities.test_utilities import DataTest
from utilities.json_utilities import load_json


def run() -> dict:
    data_test = DataTest(name="bike_and_car_parking_test")
    header, rows, statuscode, data_test = load_csv_from_url("https://data.opentransportdata.swiss/dataset/atzgf/resource_permalink/gf-datei-2025.csv", data_test=data_test)
    # loads a CSV file which has 823 bytes and 36 rows

    # example of a fatal test:
    is_status_ok = data_test.test(
        condition=(statuscode < 400),
        if_false_log_failure=f"Status Code {statuscode} is >= 400!")  # if ok, no log, silent.
    if not is_status_ok:  # this is a fatal error, therefore ending test now.
        return data_test

    # example of a test which reports a "failure" if condition not ok:
    size_is_ok = data_test.test(
            condition=("DayType" in header and "TrainNumber" in header),
            if_false_log_failure=f"Header fields {str(header)} are not ok!",
            if_true_log_info=f"Header fields are ok.")

    # example of a test which reports a warning if condition not ok:
    data_test.test(
            condition=(34 < len(rows) < 38),
            if_false_log_warning=f"Rows are not as expected, len(rows)={len(rows)}!",
            if_true_log_info=f"Row count is ok, len(rows)={len(rows)}.")

    # add some extra example messages directly:
    data_test.log_info("An extra example info message.")
    data_test.log_warning("An extra example warning message.")
    data_test.log_failure("An extra example failure message.")
    data_test.log_exception("An extra example excpetion message.", ValueError("Example ValueError"))

    # at the end, return the data_test object, it contains the logs and the counts (warnings, failures, etc.):
    return data_test


if __name__ == '__main__':
    tr = run()
    print(tr)
    print(tr.to_dict())
