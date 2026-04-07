"""
Test the gtfs files.
The run method requires no config at all (hence, no 'config' parameter).
"""

from utilities.test_utilities import DataTest
from utilities.gtfs_utilities import check_gtfs


def run():
    data_test = DataTest(name="gtfs_checker_test")

    gtfs_2026_url = "https://data.opentransportdata.swiss/dataset/timetable-2026-gtfs2020/permalink"
    gtfs_fahrplanentwurf_url = "https://data.opentransportdata.swiss/dataset/timetable-draft-gtfs/permalink"

    check_gtfs(gtfs_2026_url, data_test)
    data_test.log_info("GTFS 2026 Schema check completed.")
    check_gtfs(gtfs_fahrplanentwurf_url, data_test)
    data_test.log_info("GTFS Fahrplanentwurf check completed.")

    return data_test

if __name__ == '__main__':
    tr = run()
    print(tr)