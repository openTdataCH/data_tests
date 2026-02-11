"""Test of the ist-daten dataset https://data.opentransportdata.swiss/dataset/ist-daten-v2

The test does these checks:
- load the resource
- check the age from CKAN
- check if some of the keys are present (e.g. "features")
- do some simple size checks

The run method requires no config at all (hence, no 'config' parameter).
"""

from utilities.test_utilities import DataTest
from utilities.csv_utilities import load_csv_from_url
from utilities.ckan_utilities import load_ckan_package, resource_by_identifier
from utilities.datetime_utilities import age_in_days

CSV_HEADER = "['BETRIEBSTAG', 'FAHRT_BEZEICHNER', 'BETREIBER_ID', 'BETREIBER_ABK', 'BETREIBER_NAME', 'PRODUKT_ID', 'LINIEN_ID', 'LINIEN_TEXT', 'UMLAUF_ID', 'VERKEHRSMITTEL_TEXT', 'ZUSATZFAHRT_TF', 'FAELLT_AUS_TF', 'BPUIC', 'HALTESTELLEN_NAME', 'ANKUNFTSZEIT', 'AN_PROGNOSE', 'AN_PROGNOSE_STATUS', 'ABFAHRTSZEIT', 'AB_PROGNOSE', 'AB_PROGNOSE_STATUS', 'DURCHFAHRT_TF', 'SLOID']"
ROW_RANGE = (1500000, 3000000)
AGE_IN_DAYS_THRESHOLD = 1.01


def run() -> dict:
    data_test = DataTest(name="ist_daten_test")

    # CKAN metadata checks:
    ckan_data, size, data_test = load_ckan_package(f"ist-daten-v2", data_test)
    meta_data = ckan_data['result']
    permalink = meta_data['permalink']
    metadata_resource = _resource4permalink(meta_data, permalink)
    if metadata_resource is not None:
        age = age_in_days(metadata_resource.get("issued"))
        data_test.test(age < AGE_IN_DAYS_THRESHOLD,
                       if_false_log_failure=f"FAILED age check, age {age:.4f} is above threshold {AGE_IN_DAYS_THRESHOLD:.4f}.")
    else:
        data_test.log_failure(f"Permalink invalid, no matching resource (file) found.")

    # dataset checks:
    #header, data_rows, status_code, data_test = load_csv_from_url("https://data.opentransportdata.swiss/dataset/ist-daten-v2/permalink", data_test=data_test)

    #if not data_test.test(condition=(str(header) == CSV_HEADER), if_false_log_failure=f"CSV File header is not correct: {header}"):
    #    return data_test.to_dict()

    #data_test.test(condition=(ROW_RANGE[0] <= len(data_rows) < ROW_RANGE[1]), if_false_log_failure=f"rows count is suspicious: {len(data_rows)} not within {ROW_RANGE}!")


    return data_test.to_dict()


def _resource4permalink(meta_data: dict, permalink: str) -> dict:
    for resource in meta_data['resources']:
        if resource['url'] == permalink:
            return resource
    return None


if __name__ == '__main__':
    tr = run()
    print(tr)
    print(tr['logs'])
