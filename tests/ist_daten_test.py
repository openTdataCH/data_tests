"""Test of the ist-daten dataset https://data.opentransportdata.swiss/dataset/ist-daten-v2

The test does these checks:
- load the resource
- check the age from CKAN
- check if some of the keys are present (e.g. "features")
- do some simple size checks

The run method requires no config at all (hence, no 'config' parameter).
"""

from utilities.ckan_utilities import load_ckan_package
from utilities.csv_utilities import load_csv_streaming_and_do_data_checks
from utilities.datetime_utilities import age_in_days
from utilities.test_utilities import DataTest

CSV_HEADER = "['BETRIEBSTAG', 'FAHRT_BEZEICHNER', 'BETREIBER_ID', 'BETREIBER_ABK', 'BETREIBER_NAME', 'PRODUKT_ID', 'LINIEN_ID', 'LINIEN_TEXT', 'UMLAUF_ID', 'VERKEHRSMITTEL_TEXT', 'ZUSATZFAHRT_TF', 'FAELLT_AUS_TF', 'BPUIC', 'HALTESTELLEN_NAME', 'ANKUNFTSZEIT', 'AN_PROGNOSE', 'AN_PROGNOSE_STATUS', 'ABFAHRTSZEIT', 'AB_PROGNOSE', 'AB_PROGNOSE_STATUS', 'DURCHFAHRT_TF', 'SLOID']"
ROW_RANGE = (1500000, 3000000)
AGE_IN_DAYS_THRESHOLD = 1.01


def run():
    data_test = DataTest(name="ist_daten_test", skip_logging_after=100)

    # CKAN metadata checks:
    meta_data, size, data_test = load_ckan_package(f"ist-daten-v2", data_test)
    permalink = meta_data['permalink']
    metadata_resource = _resource4permalink(meta_data, permalink)
    if metadata_resource is not None:
        age = age_in_days(metadata_resource.get("issued"))
        data_test.test(age < AGE_IN_DAYS_THRESHOLD,
                       if_false_log_failure=f"FAILED age check, age {age:.4f} is above threshold {AGE_IN_DAYS_THRESHOLD:.4f}.")
    else:
        data_test.log_failure(f"Permalink invalid, no matching resource (file) found.")

    # dataset checks:
    COLUMN_HEADERS = "BETRIEBSTAG;FAHRT_BEZEICHNER;BETREIBER_ID;BETREIBER_ABK;BETREIBER_NAME;PRODUKT_ID;LINIEN_ID;LINIEN_TEXT;UMLAUF_ID;VERKEHRSMITTEL_TEXT;ZUSATZFAHRT_TF;FAELLT_AUS_TF;BPUIC;HALTESTELLEN_NAME;ANKUNFTSZEIT;AN_PROGNOSE;AN_PROGNOSE_STATUS;ABFAHRTSZEIT;AB_PROGNOSE;AB_PROGNOSE_STATUS;DURCHFAHRT_TF;SLOID".split(";")
    COLUMN_RE_MATCHES = [
        r"^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.20[234](\d{1})$"
    ]
    data_test = load_csv_streaming_and_do_data_checks(url="https://data.opentransportdata.swiss/dataset/ist-daten-v2/permalink",
                                                      column_headers=COLUMN_HEADERS, column_re_matches=COLUMN_RE_MATCHES,
                                                      line_count_range=ROW_RANGE,
                                                      data_test=data_test)

    return data_test


def _resource4permalink(meta_data: dict, permalink: str) -> dict:
    for resource in meta_data['resources']:
        if resource['url'] == permalink:
            return resource
    return None


if __name__ == '__main__':
    tr = run()
    print(tr)
    print(tr['logs'])
