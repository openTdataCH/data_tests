"""Test the on demand files

The test does these checks:
- GTFS Flex Schema check
- NeTEx Schema check
- HRDF Schema check

The run method requires no config at all (hence, no 'config' parameter).
"""

from utilities.test_utilities import DataTest
from utilities.gtfs_utilities import check_gtfs

def run():
    data_test = DataTest(name="on_demand_test")

    gtfs_url = "https://data.opentransportdata.swiss/dataset/gtfsflex/permalink"

    check_gtfs(gtfs_url, data_test)
    data_test.log_info("GTFS Flex Schema successfully checked")

    return data_test

if __name__ == '__main__':
    tr = run()
    print(tr)