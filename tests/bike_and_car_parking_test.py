"""Test of the new bike-and-car-parking dataset

The test does these checks:
- load the resource
- check if some of the keys are present (e.g. "features")
- do some simple size checks

The run method requires no config at all (hence, no 'config' parameter).
"""

from utilities.test_utilities import DataTest
from utilities.json_utilities import load_json


def run() -> dict:
    data_test = DataTest(name="bike_and_car_parking_test")
    data, size, data_test = load_json("https://data.opentransportdata.swiss/dataset/bike-and-car-parking/permalink", data_test=data_test)

    if not data_test.test(condition=data.get("features") is not None, if_false_log_failure="JSON response has no 'features' key!"):
        return data_test.to_dict()

    if not data_test.test(condition=(2400 <= len(data["features"]) < 3000), if_false_log_failure=f"'features' have an unusual, suspicious count: {len(data['features'])}!"):
        return data_test.to_dict()

    if not data_test.test(condition=(8000000 <= size < 9999000), if_false_log_failure=f"suspicious size: {size}, not in range 8000000..9999000!"):
        return data_test.to_dict()

    data_test.log_info("passed all checks.")

    return data_test.to_dict()


if __name__ == '__main__':
    tr = run()
    print(tr)
    print(tr['logs'])
