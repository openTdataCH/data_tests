"""Test of the new group of 12 DATASETS "atlas-v2", which have three FLAVOURS (resources) each.

The test does these checks:
- load all 12 x 3 resources
- check if sizes are reasonable, within 10 % thresholds, using historical data and Exponential Moving Average (EMA).
- check ages in CKAN metadata, check if the data was updated in the last ca. 24 hours.

The run method requires no config at all (hence, no 'config' parameter).
"""

from collections import defaultdict

from utilities.ckan_utilities import load_ckan_package, resource_by_identifier
from utilities.csv_utilities import load_csv_from_url, load_csv_streaming_and_do_data_checks
from utilities.datetime_utilities import age_in_days
from utilities.json_utilities import load_json_file, save_json_file
from utilities.test_utilities import DataTest

REF_SIZES_FILE = "tests/atlas_v2_tests/data/atlas_v2_test_sizes.json"
SCHEMA_CONFIG_FILE = "tests/atlas_v2_tests/data/atlas_v2_schema_config.json"
DATASETS = [ "business-organisation", "contact-point", "line", "parking-lot", "platform", "reference-point",
             "relation", "sectors-and-sector-groups", "service-point", "stop-point", "subline", "toilet",
             "traffic-point", "timetable-field-number"]
FLAVOURS = ["timetable-years", "full", "actual-date"]
TEST_NAME = "atlas_v2_tests"
SIZE_THRESHOLDS = [0.8, 1.2]
AGE_IN_DAYS_THRESHOLD = 1.01
ALPHA = 0.2  # alpha factor for the Exponential Moving Average (EMA) of the sizes

CKAN_BASE_URL = "https://data.opentransportdata.swiss/dataset"

def run() -> dict:
    data_test = DataTest(name=TEST_NAME)
    ref_sizes = load_json_file(REF_SIZES_FILE)
    schema_master = load_json_file(SCHEMA_CONFIG_FILE)
    csv_schema_spec = schema_master.get("csv_schema_spec", {}) if schema_master else {}

    if schema_master is None:
        data_test.log_warning(f"Schema config file {SCHEMA_CONFIG_FILE} is missing or invalid JSON.")

    sizes = defaultdict(lambda : {})
    sucesses = ""
    for dataset in DATASETS:
        meta_data, size, data_test = load_ckan_package(f"{dataset}-v2", data_test)
        for i, flavour in enumerate(FLAVOURS):
            try:
                region = "swiss-" if dataset == "service-point" else ("world-" if dataset == "traffic-point" else "")
                identifier = f"{flavour}-{region}{dataset}.csv"
                url = f"{CKAN_BASE_URL}/{dataset}-v2/resource_permalink/{identifier}"
                header, rows, status_code, data_test = load_csv_from_url(url, data_test=data_test, silent=True)
                if status_code < 400:
                    file_schema = csv_schema_spec.get(identifier)
                    if file_schema:
                        data_test = load_csv_streaming_and_do_data_checks(
                            url=url,
                            schema_config=file_schema,
                            delimiter=";",
                            filename=identifier,
                            data_test=data_test,
                        )
                    else:
                        data_test.log_warning(f"No schema configuration for '{identifier}' found in {SCHEMA_CONFIG_FILE}.")

                    if ref_sizes:
                        ref_sizes_ds = ref_sizes.get(dataset)
                        if ref_sizes_ds:
                            ref_size = ref_sizes_ds.get(flavour)
                            if ref_size is not None and type(ref_size) is int:
                                if not (SIZE_THRESHOLDS[0] * ref_size < size < SIZE_THRESHOLDS[1] * ref_size):
                                    data_test.log_warning(f"Resource size {size} is not within {SIZE_THRESHOLDS} of reference size {ref_size}.")
                                    size = round(ALPHA * size + (1 - ALPHA) * ref_size) # Exponential Moving Average (EMA)
                    sizes[dataset][flavour] = size

                    metadata_resource = resource_by_identifier(meta_data, identifier)
                    age = age_in_days(metadata_resource.get("issued"))
                    if age >= AGE_IN_DAYS_THRESHOLD:
                        data_test.log_failure(f"FAILED age check, age {age:.3f} days is above threshold {AGE_IN_DAYS_THRESHOLD:.3f} days.\n--> {CKAN_BASE_URL}/{dataset}-v2 --> {flavour}")
                    else:
                        sucesses = sucesses + identifier + ', '
                else:
                    data_test.log_failure(f"Response {status_code} for {identifier}.")
                    data_test.log_info(f"- dataset: {CKAN_BASE_URL}/{dataset}-v2")
                    data_test.log_info(f"- harvester: {CKAN_BASE_URL}/{dataset}-v2-harvester")

            except Exception as e:
                data_test.log_exception(f"Data test for {dataset}/{flavour} failed with exception: {e}", e)

    data_test.log_info(f"Sucessfully tested: {sucesses[:-2]}.")

    save_json_file(REF_SIZES_FILE, sizes)

    return data_test


if __name__ == '__main__':
    tr = run()
    print(tr)
