"""A utility for service points data.
- Uses the actual-date file from https://data.opentransportdata.swiss/dataset/service-point-v2
- takes care of automatic loading, caching and daily refreshing of the file.
- gives access to any service point through a simple get_service_point() method.

Usage example:
sp = get_service_point('number', '1322044')
print(sp['designationOfficial'])

"""
import math

import os
import requests

from utilities.csv_utilities import load_csv_from_file
from utilities.file_and_path_utilities import get_path, file_age_in_days_if_exists


SP_PERMALINK = "https://data.opentransportdata.swiss/dataset/service-point-v2/resource_permalink/actual-date-swiss-service-point.csv"
SP_DIR = "utilities/service_points_utilities/data"
SP_FILEPATH = F"{SP_DIR}/actual-date-swiss-service-point.csv"
SP_FILE_AGE_THRESHOLD = 1.0
sps = None


def _load_service_points():
    if not os.path.exists(get_path(SP_DIR)):
        os.mkdir(get_path(SP_DIR))
    global sps
    age = file_age_in_days_if_exists(SP_FILEPATH)
    if age is None or age > SP_FILE_AGE_THRESHOLD:
        response = requests.get(SP_PERMALINK)
        response.raise_for_status()
        with open(get_path(SP_FILEPATH), "wb") as file:
            file.write(response.content)

    s = load_csv_from_file(SP_FILEPATH, encoding='utf-8-sig')
    sps =  [{s[0][i]: (r[i] if i < len(r) else None) for i in range(len(s[0]))} for r in s[1:]]


_load_service_points()


def get_service_point(key: str, value: str) -> dict:
    """Looks for a service point which has the given value at the given key. Returns it as a dict, or None if not found."""
    for sp in sps:
        if sp.get(key) == value:
            return sp
    return None

def sp_name(number: str) -> str:
    """Convenience function go get the service point name 'designationOfficial' for a given BPUIC number. """
    sp = get_service_point('number', str(number))
    return "" if sp is None else sp['designationOfficial']


def approx_distance_m(sp1_number: str, sp2_number: str) -> float:
    """Calculate the approximate distance between two services points in meters, or -1.0 if calculation fails."""
    try:
        sp1 = get_service_point('number', sp1_number)
        sp2 = get_service_point('number', sp2_number)
        c1 = float(sp1['lv95East']), float(sp1['lv95North'])
        c2 = float(sp2['lv95East']), float(sp2['lv95North'])
        return math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2)

    except:
        return -1.0






if __name__ == '__main__':
    print(f"{__file__} - simple tests")
    sp8589008 = get_service_point('number', '8589008')
    print(f"Looked up service point {sp8589008}.")
    assert sp8589008 is not None
    assert sp8589008['designationOfficial'] == 'Bern, Wyleregg'

    sp8576993 = get_service_point('designationOfficial', 'Papiermühle, Bahnhof')
    print(f"Looked up service point {sp8576993}.")
    assert sp8576993 is not None
    assert sp8576993['number'] == '8576993'

    approx_distance = approx_distance_m(sp8589008['number'], sp8576993['number'])
    print(f"Approx distance {approx_distance:.1f} m.")
    assert abs(approx_distance - 2560) < 100

    print("all well.")

