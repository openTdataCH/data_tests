"""Test the on demand files

The test does these checks:
- GTFS Flex Schema check
- NeTEx Schema check
- HRDF Schema check

The run method requires no config at all (hence, no 'config' parameter).
"""
from tests.on_demand_tests.netex_utilities import check_netex
from tests.on_demand_tests.hrdf_utilities import check_hrdf
from utilities.test_utilities import DataTest
from utilities.gtfs_utilities import check_gtfs

def run():
    data_test = DataTest(name="on_demand_test")

    gtfs_url = "https://data.opentransportdata.swiss/dataset/gtfsflex/permalink"
    netex_url = "https://data.opentransportdata.swiss/dataset/netex_tt_odv/permalink"
    hrdf_url = "https://data.opentransportdata.swiss/dataset/hrdf_odv/permalink"

    check_gtfs(gtfs_url, data_test)
    data_test.log_info("GTFS Flex Schema check completed.")
    check_netex(netex_url, data_test)
    data_test.log_info("NETEX Schema check completed.")
    check_hrdf(url=hrdf_url, data_test=data_test, ignore_bitfield_file_check=True)
    data_test.log_info("HRDF Schema check completed.")

    return data_test

if __name__ == '__main__':
    tr = run()
    print(tr)