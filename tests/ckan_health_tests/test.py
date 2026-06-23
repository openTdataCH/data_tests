"""Tests of the CKAN data catalog of opentransportdata.swiss, including harvesters.
Doing some basic checks on many datasets and harvesters, about things that frequently go wrong:
- harvesters: check if latest job not "finished" and older than 15 minutes: ["status"]["last_job"]["created"] und ["status"]["last_job"]["status"] (!="Finished")
- harvesters: check if those of type "MANUAL" and having note "cron" were run in the last 24 h.
- datasets (selected): check if the URL of the newest resource is equal to the permlink URL.
- datasets (selected): check if they are up to date (either < 24 h or bi-weekly, e.g. for GTFS).

In case of failures, provide helpful messages for fixing the problem.
"""

from utilities.ckan_utilities import load_ckan_package_list, load_ckan_package
from utilities.test_utilities import DataTest
from utilities.datetime_utilities import age_in_days
from utilities.json_utilities import load_json_file, save_json_file
from datetime import datetime as dt, timezone, timedelta


NOW = dt.now(timezone.utc)
TEST_NAME = "ckan_health_tests"
CONFIG_FILE = f"tests/{TEST_NAME}/data/config.json"
config = load_json_file(CONFIG_FILE)
if not config:
    raise FileNotFoundError(f"Config file not found at {CONFIG_FILE}")

DS_PATH = f"tests/{TEST_NAME}/data/datasets.json"
EXCLUDED_DATASETS = config["excluded_datasets"]
EXCLUDED_PERMALINK_AGE_CHECK = config["excluded_permalink_age_check"]
DATASETS_WITH_RESSOURCES_OF_UNLIMITED_AGE = config["datasets_with_resources_of_unlimited_age"]
LESS_THAN_DAILY_UPDATES_UTC = config["less_than_daily_updates_utc"]
MINIMUM_ACCEPTABLE_AGE = config["minimum_acceptable_age"]
DEFAULT_ACCEPTABLE_AGE = config["default_acceptable_age"]
EXCLUDED_NON_DAILY_CRONS = config["excluded_non_daily_crons"]

def get_datasets(data_test: DataTest) -> dict:
    """Gets a dict with dataset id (slug)/identifier as key/value pairs; if not in available at DS_PATH, load and save it.
     The Identifiers are needed later on for the mapping to the harvester(s)."""
    ds = load_json_file(DS_PATH)
    if ds is not None:
        return ds
    else:
        try:
            ds = {}
            package_list, _ = load_ckan_package_list(data_test)
            for package in package_list:
                package_metadata, _, _ = load_ckan_package(package, data_test)
                if package_metadata.get('type') == "dataset":
                    ds[package] = package_metadata.get('identifier')
            save_json_file(DS_PATH, ds)
            data_test.log_info(f"Loaded datasets list with {len(ds)} datasets and saved to cache.")
            return ds
        except Exception as e:
            data_test.log_exception(f"get_datasets failed with {str(e)}", e)
            return {}

def check_harvesters(harvesters: list, data_test: DataTest) -> dict:
    harvester_to_datasets_mapping = {}
    count_hanging, count_too_old = 0, 0
    for harvester in [h for h in harvesters if h not in EXCLUDED_NON_DAILY_CRONS]:
        meta_data, size, data_test = load_ckan_package(harvester, data_test)

        # The "dataset" attribute is needed for the link from dataset to harvester (needed later on).
        # If it contains a {year} placeholder, replace this with possible years (NOW +/- 3 years)
        dataset = meta_data.get('dataset')
        if dataset:
            values = [dataset.replace('{year}', str(y)) for y in range(NOW.year - 3, NOW.year + 4)] if "{year}" in dataset else [dataset]
            for value in values:
                harvester_to_datasets_mapping[value] = harvester

        # CKAN stores created date here as UTC but without TZ extension, add it:
        if meta_data.get("status") and meta_data["status"].get("last_job"):
            last_job = meta_data["status"]["last_job"]
            last_job_age = age_in_days(last_job.get("created") + "+00:00")
            last_job_status = last_job.get("status")
            if last_job_age > 0.5 / 24.0 and last_job_status != "Finished":
                data_test.log_failure(f"CKAN hanging harvester? '{harvester}' is running and older than 30 minutes!")
                count_hanging += 1
            gather_error_summary = last_job.get("gather_error_summary")
            if gather_error_summary and len(gather_error_summary) > 0:
                data_test.log_failure(f"CKAN harvester " + str(harvester) + " last_job had an error: " + str(gather_error_summary) + " !")
                #data_test.log_failure(f"CKAN harvester '{harvester}' last_job had an error: {str(gather_error_summary).replace('\n', '')}!")
            frequency = meta_data.get("frequency")
            notes_lc = str(meta_data.get("notes")).lower()
            if last_job_age > 1.0 and frequency == "MANUAL" and "cron" in notes_lc:
                data_test.log_failure(f"CKAN missed cron run? '{harvester}' age is {last_job_age:.4f} days!")
                count_too_old += 1
        else:
            data_test.log_warning(f"No valid status/last_job for '{harvester}' found in metadata!")
    data_test.log_info(f"CKAN harvester tests: Checked {len(harvesters)}: {count_hanging} hanging, {count_too_old} older than a day.")

    return harvester_to_datasets_mapping

def _get_past_instant(target_weekday_str, target_hour):
    WD = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
    target_weekday = WD.get(target_weekday_str.lower()[0:3])
    # Calculate days difference to get to the target weekday in the past
    days_diff = (NOW.weekday() - target_weekday) % 7

    # If the target weekday is today and the hour is greater than now, go back a week
    if days_diff == 0 and NOW.hour < target_hour:
        days_diff = 7

    # Calculate the past target instant
    past_instant = NOW - timedelta(days=days_diff)
    past_instant = past_instant.replace(hour=target_hour, minute=0, second=0, microsecond=0)

    return past_instant


def _acceptable_age_in_days(dataset):
    if dataset in DATASETS_WITH_RESSOURCES_OF_UNLIMITED_AGE:
        return 999999.99

    if dataset in LESS_THAN_DAILY_UPDATES_UTC.keys():
        due_on = [d.strip() for d in LESS_THAN_DAILY_UPDATES_UTC[dataset].split(",")]
        min_age_d = 999999.99
        for d in due_on:
            weekday, hour = d[0:3], int(d[3:5])
            past_instant = _get_past_instant(weekday, hour)
            age = NOW - past_instant
            age_d = age.days + age.seconds / 86400.0
            min_age_d = min(min_age_d, age_d)
        return min_age_d + MINIMUM_ACCEPTABLE_AGE

    return DEFAULT_ACCEPTABLE_AGE


def _canonized_permalink(permalink: str) -> str:
    """Returns a canonical form of a permalink, removing language short-strings /de/, /fr/, /it/, /en/."""
    return permalink.replace("/de/", "/").replace("/en/", "/").replace("/fr/", "/").replace("/it/", "/")



def check_datasets_permalink_and_age(datasets: dict, harvester_to_datasets_mapping: dict, data_test: DataTest):
    count_permalink_fails, count_age_fails = 0, 0
    for dataset in sorted(list(datasets.keys())):
        if dataset not in EXCLUDED_DATASETS:
            ds_metadata, _, _ = load_ckan_package(dataset, data_test)
            if not ds_metadata:
                data_test.log_warning(f"No metadata found for '{dataset}', has been deleted? (you can delete {DS_PATH} to have datasets list reloaded).")
            else:
                resources = ds_metadata.get("resources")
                min_age = 999999.9
                id = datasets.get(dataset)
                harvester_id = harvester_to_datasets_mapping.get(id)
                ds_link = f"\n--> dataset: https://data.opentransportdata.swiss/dataset/{dataset}"
                hv_link = f"\n--> harvester: https://data.opentransportdata.swiss/harvest/{harvester_id}" if harvester_id else ""
                latest_resource_permalink = None
                for resource in resources:
                    age_of_resource = age_in_days(resource.get('created'))
                    if age_of_resource < min_age:
                        latest_resource_permalink = resource.get('url')
                        min_age = age_of_resource

                if not (dataset in EXCLUDED_PERMALINK_AGE_CHECK):
                    permalink = ds_metadata.get("permalink")
                    if _canonized_permalink(permalink) != _canonized_permalink(latest_resource_permalink):
                        data_test.log_failure(f"Dataset '{dataset}': Permalink not matching latest resource URL!{ds_link}{hv_link}")
                        count_permalink_fails += 1

                acceptable_age = _acceptable_age_in_days(dataset)
                if min_age > acceptable_age:
                    data_test.log_failure(f"Dataset '{dataset}': Age of latest resource is {min_age:.3f} days, exceeds acceptable age of {acceptable_age:.3f} days!{ds_link}{hv_link}")
                    count_age_fails += 1

    data_test.log_info(f"CKAN dataset tests: Checked {len(datasets)}, {count_permalink_fails} permalink errors, {count_age_fails} exceeding acceptable age.")


def run():
    data_test = DataTest(name=TEST_NAME)
    packages, data_test = load_ckan_package_list(data_test)

    harvesters = [h for h in packages if 'harvester' in h]
    harvester_to_datasets_mapping = check_harvesters(harvesters, data_test)

    datasets = get_datasets(data_test)
    check_datasets_permalink_and_age(datasets, harvester_to_datasets_mapping, data_test)

    return data_test


if __name__ == '__main__':
    tr = run()
    print(tr)
