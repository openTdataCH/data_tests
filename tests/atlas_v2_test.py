"""Test of the new group of 12 DATASETS "atlas-v2", which have three FLAVOURS (resources) each.

The test does these checks:
- load all 12 x 3 resources
- check if sizes are reasonable, within 10 % thresholds, using historical data and Exponential Moving Average (EMA).
- check ages in CKAN metadata, check if the data was updated in the last ca. 24 hours.

The run method requires no config at all (hence, no 'config' parameter).
"""

from collections import defaultdict

from utilities.ckan_utilities import load_ckan_package, resource_by_identifier
from utilities.csv_utilities import load_csv_from_url
from utilities.datetime_utilities import age_in_days
from utilities.json_utilities import load_json_file, save_json_file
from utilities.test_utilities import DataTest

REF_SIZES_FILE = "data/persistent_test_data/atlas_v2_test_sizes.json"
DATASETS = [ "business-organisation", "contact-point", "line", "parking-lot", "platform", "reference-point",
             "relation", "service-point", "stop-point", "subline", "toilet", "traffic-point"]
FLAVOURS = ["timetable-years", "full", "actual-date"]
SIZE_THRESHOLDS = [0.9, 1.1]
AGE_IN_DAYS_THRESHOLD = 0.9
ALPHA = 0.2  # alpha factor for the Exponential Moving Average (EMA) of the sizes


def run() -> dict:
    data_test = DataTest(name="atlas_v2_test")
    ref_sizes = load_json_file(REF_SIZES_FILE)
    sizes = defaultdict(lambda : {})
    for dataset in DATASETS:
        ckan_data, size, data_test = load_ckan_package(f"{dataset}-v2", data_test)
        meta_data = ckan_data['result']
        for i, flavour in enumerate(FLAVOURS):
            try:
                region = "swiss-" if dataset == "service-point" else ("world-" if dataset == "traffic-point" else "")
                identifier = f"{flavour}-{region}{dataset}.csv"
                url = f"https://data.opentransportdata.swiss/dataset/{dataset}-v2/resource_permalink/{identifier}"
                header, rows, status_code, data_test = load_csv_from_url(url, data_test=data_test)
                if status_code < 400:
                    if ref_sizes:
                        ref_sizes_ds = ref_sizes.get(dataset)
                        if ref_sizes_ds:
                            ref_size = ref_sizes_ds.get(flavour)
                            if ref_size is not None and type(ref_size) is int:
                                data_test.test(SIZE_THRESHOLDS[0] * ref_size < size < SIZE_THRESHOLDS[1] * ref_size,
                                               if_true_log_info=f"Passed size check, has {len(rows)} rows.",
                                               if_false_log_warning=f"Resource size {size} is not within {SIZE_THRESHOLDS} of reference size {ref_size}.")
                                size = round(ALPHA * size + (1 - ALPHA) * ref_size) # Exponential Moving Average (EMA)
                    sizes[dataset][flavour] = size

                    metadata_resource = resource_by_identifier(meta_data, identifier)
                    age = age_in_days(metadata_resource.get("issued"))
                    data_test.test(age < AGE_IN_DAYS_THRESHOLD,
                                   if_true_log_info=f"Passed age check, age {age:.4f} is below threshold {AGE_IN_DAYS_THRESHOLD:.4f}.",
                                   if_false_log_failure=f"FAILED age check, age {age:.4f} is above threshold {AGE_IN_DAYS_THRESHOLD:.4f}.")
            except Exception as e:
                data_test.log_exception(f"Data test for {dataset}/{flavour} failed with exception: {e}", e)

    save_json_file(REF_SIZES_FILE, sizes)

    return data_test.to_dict()


if __name__ == '__main__':
    tr = run()
    print(tr)
    print(tr['logs'])
