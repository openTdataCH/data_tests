"""A utility for service points data.
- Uses the actual-date file from https://data.opentransportdata.swiss/dataset/service-point-v2
- takes care of automatic loading, caching and daily refreshing of the file.
- gives access to any service point through a simple get_service_point() method.

Usage example:
sp = get_service_point('number', '1322044')
print(sp['designationOfficial'])

"""
import os
import requests

from utilities.csv_utilities import load_csv_from_file
from utilities.file_and_path_utilities import get_path, file_age_in_days_if_exists


SP_PERMALINK = "https://data.opentransportdata.swiss/dataset/service-point-v2/resource_permalink/actual-date-swiss-service-point.csv"
SP_FILEPATH = "utilities/service_points_utilities/data/actual-date-swiss-service-point.csv"
SP_FILE_AGE_THRESHOLD = 1.0
sps = None


def _load_service_points():
    if not os.path.exists('data'):
        os.mkdir('data')
    global sps
    age = file_age_in_days_if_exists(SP_FILEPATH)
    if age is None or age > SP_FILE_AGE_THRESHOLD:
        response = requests.get(SP_PERMALINK)
        response.raise_for_status()
        with open(get_path(SP_FILEPATH), "wb") as file:
            file.write(response.content)
        print(f"reloaded file {SP_FILEPATH}")

    s = load_csv_from_file(SP_FILEPATH, encoding='utf-8-sig')
    sps =  [{s[0][i]: (r[i] if i < len(r) else None) for i in range(len(s[0]))} for r in s[1:]]


_load_service_points()


def get_service_point(key: str, value: str) -> dict:
    """Looks for a service point which has the given value at the given key. Returns it as a dict, or None if not found."""
    for sp in sps:
        if sp.get(key) == value:
            return sp
    return None



if __name__ == '__main__':
    print(f"{__file__} - simple tests")
    sp1322044 = get_service_point('number', '1322044')
    assert sp1322044 is not None
    assert sp1322044['designationOfficial'] == 'Gravellona Toce, bivio FS'
    print(get_service_point('number', '1322044'))
    print("all well.")

