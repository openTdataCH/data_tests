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
DS_PATH = "tests/ckan_health_tests/data/datasets.json"


def get_datasets(data_test: DataTest) -> list:
    ds = load_json_file(DS_PATH)
    if ds is not None:
        return ds
    else:
        try:
            ds = []
            package_list, _ = load_ckan_package_list(data_test)
            for package in package_list:
                package_metadata, _, _ = load_ckan_package(package, data_test)
                if package_metadata.get('type') == "dataset":
                    ds.append(package)
            save_json_file(DS_PATH, ds)
            data_test.log_info(f"Loaded datasets list with {len(ds)} datasets and saved to cache.")
            return ds
        except Exception as e:
            data_test.log_exception(f"get_datasets failed witth {str(e)}", e)
            return None


EXCLUDED_NON_DAILY_CRONS = ('gtfs2020-harvester', )

def check_harvesters(harvesters: list, data_test: DataTest):
    count_hanging, count_too_old = 0, 0
    for harvester in [h for h in harvesters if h not in EXCLUDED_NON_DAILY_CRONS]:
        meta_data, size, data_test = load_ckan_package(harvester, data_test)
        # CKAN stores created date here as UTC but without TZ extension, add it:
        last_job_age = age_in_days(meta_data["status"]["last_job"]["created"] + "+00:00")
        last_job_status = meta_data["status"]["last_job"]["status"]
        if last_job_age > 0.5 / 24.0 and last_job_status != "Finished":
            data_test.log_failure(f"CKAN hanging harvester? '{harvester}' is running and older than 30 minutes!")
            count_hanging += 1
        frequency = meta_data.get("frequency")
        notes_lc = str(meta_data.get("notes")).lower()
        if last_job_age > 1.0 and frequency == "MANUAL" and "cron" in notes_lc:
            data_test.log_failure(f"CKAN missed cron run? '{harvester}' age is {last_job_age:.4f} days!")
            count_too_old += 1
    data_test.log_info(f"CKAN harvester tests: Checked {len(harvesters)}: {count_hanging} hanging, {count_too_old} older > 1 day.")


EXCLUDED_DATASETS = ('business-organisations', 'formations', 'gtfsrt', 'gtfs-sa', 'halte', 'hrdf_test_207',
                    'lod-pilot', 'netex-fernbus', 'ojp2-0', 'ojp2020', 'ojpfare', 'osdm-offline', 'rds-tmc',
                    'siri-et', 'siri-pt', 'siri-sx', 'trafficcountersrealtime', 'trafficlights-road-dynamic',
                    'trafficsituations', 'vm-liste')
DATASETS_WITH_RESSOURCES_OF_UNLIMITED_AGE = (
    'atzgf', 'einundaus', 'ereignisinformationen', 'ga-hta-liste1', 'go-realtime', 'go-siri-sx', 'go-siri-sx-infra',
    'ladestationen', 'sharedmobility', 'timetable-draft-gtfs', 'verbundsabos', 'vnch-swisstne', 'zugzahlen',
    'netex-fernbus', 'timetable-2024-gtfs2020', 'timetable-2025-gtfs2020', 'list-sjyid',
    'timetable-54-2024-hrdf-autoverlad', 'timetable-54-2025-hrdf-autoverlad',
    'list-sjyid-2025', 'list-sjyid-2025-v2',
    'timetable-54-2024-hrdf', 'timetable-54-2025-hrdf', 'timetable-54-draft-hrdf',
    'timetablenetex_2024', 'timetablenetex_2025', 'trafficcounters', 'trafficlights-road-static')
LESS_THAN_DAILY_UPDATES_UTC = {
    'gtfsflex': 'MON09,THU09',
    'timetable-2026-gtfs2020': 'THU08,MON08',
    'list-sjyid-2026': 'TUE22,FRI22',
    'list-sjyid-2026-v2': 'TUE22,FRI22',
    'timetable-54-2026-hrdf-autoverlad': 'TUE21,FRI21',
    'timetable-54-2026-hrdf': 'TUE21,FRI21',
    'hrdf_odv': 'TUE08,FRI08',
    'netex_tt_odv': 'MON09,THU09',
    'timetablenetex_2026': 'TUE01,FRI01'
}
MINIMUM_ACCEPTABLE_AGE = 0.25
DEFAULT_ACCEPTABLE_AGE = 1.1


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
        due_on = LESS_THAN_DAILY_UPDATES_UTC[dataset].split(",")
        min_age_d = 999999.99
        for d in due_on:
            weekday, hour = d[0:3], int(d[3:5])
            past_instant = _get_past_instant(weekday, hour)
            age = NOW - past_instant
            age_d = age.days + age.seconds / 86400.0
            min_age_d = min(min_age_d, age_d)
        return min_age_d + MINIMUM_ACCEPTABLE_AGE

    return DEFAULT_ACCEPTABLE_AGE


def check_datasets_permalink_and_age(datasets: list, data_test: DataTest):
    count_permalink_fails, count_age_fails = 0, 0
    for dataset in datasets:
        if dataset not in EXCLUDED_DATASETS:
            ds_metadata, _, _ = load_ckan_package(dataset, data_test)
            if not ds_metadata:
                data_test.log_warning(f"No metadata found for '{dataset}', has been deleted? (you can delete {DS_PATH} to have datasets list reloaded).")
            else:
                resources = ds_metadata.get("resources")
                min_age = 999999.9
                latest_resource_permalink = None
                for resource in resources:
                    age_of_resource = age_in_days(resource.get('created'))
                    if age_of_resource < min_age:
                        latest_resource_permalink = resource.get('url')
                        min_age = age_of_resource

                permalink = ds_metadata.get("permalink")
                if permalink != latest_resource_permalink:
                    data_test.log_failure(f"Dataset '{dataset}': Permalink not matching latest resource URL! --> https://data.opentransportdata.swiss/dataset/{dataset}")
                    count_permalink_fails += 1

                acceptable_age = _acceptable_age_in_days(dataset)
                if min_age > acceptable_age:
                    data_test.log_failure(f"Dataset '{dataset}': Age of latest resource {min_age:.4f} exceeds acceptable age {acceptable_age:.4f}! --> https://data.opentransportdata.swiss/dataset/{dataset}")
                    count_age_fails += 1

    data_test.log_info(f"CKAN dataset tests: Checked {len(datasets)}, {count_permalink_fails} permalink errors, {count_age_fails} exceeding acceptable age.")


def run(config: dict = None):
    data_test = DataTest(name="ckan_health_test")
    packages, data_test = load_ckan_package_list(data_test)

    #harvesters = [h for h in packages if 'harvester' in h]
    #check_harvesters(harvesters, data_test)

    datasets = get_datasets(data_test)
    check_datasets_permalink_and_age(datasets, data_test)

    return data_test


if __name__ == '__main__':
    from configuration import CONFIG
    tr = run(config=CONFIG)
    print(tr)
