"""
Test the gtfs files.
The run method requires no config at all (hence, no 'config' parameter).
"""
from datetime import date

from utilities.test_utilities import DataTest
from utilities.gtfs_utilities.gtfs_utilities import check_gtfs

TEST_NAME = "gtfs_checker_tests"

def run(variant: str = None) -> DataTest:
    if variant is None:
        variant = str(date.today().year)
    data_test = DataTest(name=f"{TEST_NAME}_{variant}")
    if variant == "gtfs_fahrplanentwurf":
        check_gtfs("https://data.opentransportdata.swiss/dataset/timetable-draft-gtfs/permalink", data_test)
    else:
        check_gtfs(f"https://data.opentransportdata.swiss/dataset/timetable-{variant}-gtfs2020/permalink", data_test)

    return data_test

if __name__ == '__main__':
    tr = run()
    print(tr)