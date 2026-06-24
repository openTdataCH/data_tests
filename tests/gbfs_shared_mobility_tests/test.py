"""Test of the shared mobility / gbfs dataset https://data.opentransportdata.swiss/dataset/sharedmobility

The test does these checks:
- load two resources from opentransportdata.swiss
- do checks if data is present and if linked data is valid

The run method requires no config at all (hence, no 'config' parameter).
"""
from utilities.test_utilities import DataTest
from utilities.json_utilities import load_json
import concurrent.futures

RESOURCES = {
    "GBFS 2.3": "https://sharedmobility.ch/v2/gbfs",
    "GBFS 2.1": "https://data.opentransportdata.swiss/dataset/sharedmobility/resource_permalink/gbfs.json"
}

EXCLUDED_URLS = {
    "https://sharedmobility.ch/v2/gbfs/donkey_le_locle/system_pricing_plans",
    "https://sharedmobility.ch/v2/gbfs/bird-platform-partner-jmfleetswl-biel/system_pricing_plans",
    "https://sharedmobility.ch/v2/gbfs/bird-grenchen/system_pricing_plans",
    "https://sharedmobility.ch/v2/gbfs/bird-biel/system_pricing_plans",
    "https://sharedmobility.ch/v2/gbfs/bird-kloten/system_pricing_plans",
    "https://sharedmobility.ch/v2/gbfs/bird-platform-partner-jmfleets-bulle/system_pricing_plans",
    "https://sharedmobility.ch/v2/gbfs/bird-zurich/system_pricing_plans",
    "https://sharedmobility.ch/v2/gbfs/bird-basel/system_pricing_plans",
    "https://sharedmobility.ch/v2/gbfs/bird-schaffhausen/system_pricing_plans",
    "https://sharedmobility.ch/v2/gbfs/bird-winterthur/system_pricing_plans",
    "https://sharedmobility.ch/v2/gbfs/voiscooters.com/geofencing_zones",
    "https://sharedmobility.ch/v2/gbfs/bird-basel/geofencing_zones",
    "https://sharedmobility.ch/free_bike_status.json",
    "https://sharedmobility.ch/station_information.json",
    "https://sharedmobility.ch/v2/gbfs/bolt_zurich/geofencing_zones",
    "https://sharedmobility.ch/v2/gbfs/nextbike_ch/geofencing_zones"
}

TEST_CONFIGURATIONS_GBFS21 = [
    ("providers", 20, 100, "providers"),
    ("system_id", 5, 40, "information"),
    ("stations", 1000, float('inf'), "stations"),
    ("bikes", 1000, float('inf'), "bikes"),
    ("rental_hours", 5, 20, "hours"),
    ("regions", 5, 1000, "regions"),
    ("plans", 5, 200, "plans"),
    ("geofencing_zones.features", 10, 100, "geopoints")
]
TEST_CONFIGURATIONS_GBFS23 = [
    ("system_id", 5, 40, "information"),
    ("stations", 1, float('inf'), "stations"),
    ("bikes", 1, float('inf'), "bikes"),
    ("rental_hours", 1, 5, "hours"),
    ("regions", 1, 150, "regions"),
    ("plans", 1, 25, "plans"),
    ("vehicle_types", 1, 2000, "vehicles"),
    ("geofencing_zones.features", 1, 10000, "geopoints")
]

def validate_entity(data_test, content, key_path, min_value, max_value, label, url):
    """ checks if the entity content is valid. """
    data = content.get("data", {})
    for part in key_path.split("."):
        data = data.get(part, {}) if isinstance(data, dict) else []
    if not data:
        return
    count = len(data)
    is_valid = min_value <= count <= max_value

    data_test.test(
        condition=is_valid,
        if_false_log_failure=f"GBFS ({url}) contains not enough {label} ({count})!",
    )

def process_feed(feed_url, config_type, data_test, token):
    """Single worker-task for feed-check."""
    if not feed_url or feed_url in EXCLUDED_URLS:
        return 0, 0

    content, size, _ = load_json(feed_url, data_test=data_test, key=token)
    if not content:
        data_test.log_warning(f"Feed {feed_url} is empty!")
        return 0, size

    configs = TEST_CONFIGURATIONS_GBFS21 if config_type == "2.1" else TEST_CONFIGURATIONS_GBFS23
    for key_path, min_val, max_val, label in configs:
        validate_entity(data_test, content, key_path, min_val, max_val, label, feed_url)

    return 1, size

def run() -> DataTest:
    data_test = DataTest(name="gbfs_shared_mobility_tests")
    MY_TOKEN = "opendata@sbb.ch"
    successful_tests = 0
    loaded_bytes = 0

    tasks = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for key, url in RESOURCES.items():
            resource_data, size, _ = load_json(url, data_test=data_test, key=MY_TOKEN)
            loaded_bytes+=size
            if not resource_data: continue

            if key == "GBFS 2.1":
                feeds = resource_data.get("data", {}).get("en", {}).get("feeds", [])
                for f in feeds:
                    tasks.append(executor.submit(process_feed, f.get("url"), "2.1", data_test, MY_TOKEN))

            elif key == "GBFS 2.3":
                systems = resource_data.get("systems", [])
                for system in systems:
                    sys_url = system.get("url")
                    if not sys_url: continue

                    sys_data, size, _ = load_json(sys_url, data_test=data_test, key=MY_TOKEN)
                    loaded_bytes+=size
                    feeds = sys_data.get("data", {}).get("en", {}).get("feeds", [])
                    for f in feeds:
                        tasks.append(executor.submit(process_feed, f.get("url"), "2.3", data_test, MY_TOKEN))

        for future in concurrent.futures.as_completed(tasks):
            count, size = future.result()
            successful_tests+=count
            loaded_bytes+=size

    total_mb = loaded_bytes / 1000000
    if successful_tests > 300:
        data_test.log_info(f"{successful_tests} pages checked successfully, loaded a total of {total_mb:.6f} MB")
    else:
        data_test.log_warning(f"Only {successful_tests} of 332 pages checked successfully, loaded a total of {total_mb:.6f} MB")
    return data_test


if __name__ == '__main__':
    tr = run()
    print(tr)
    print(tr.to_dict())
