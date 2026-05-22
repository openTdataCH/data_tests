"""A test for the HRDF files

The test does these checks:
- load HRDF file (zipped) from opentransportdata.swiss
- various tests of the individual files

The run method requires no config at all (hence, no 'config' parameter).
"""
from utilities.csv_utilities import load_csv_from_url
from utilities.test_utilities import DataTest
from tests.hrdf_checker_tests import main

TEST_NAME = "hrdf_checker_tests"

def run(variant: str = None) -> DataTest:
    data_test = DataTest(name=f"{TEST_NAME}_{variant}")
    main.run(data_test, variant=variant)
    # at the end, return the data_test object, it contains the logs and the counts (warnings, failures, etc.):
    return data_test


if __name__ == '__main__':
    tr = run()
    print(tr)
    print(tr.to_dict())
