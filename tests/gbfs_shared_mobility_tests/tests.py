"""Test of the shared mobility / gbfs dataset https://data.opentransportdata.swiss/dataset/sharedmobility

The test does these checks:
- load two resources from opentransportdata.swiss
- do checks if data is present and if linked data is valid

The run method requires no config at all (hence, no 'config' parameter).
"""
from utilities.test_utilities import DataTest
from utilities.json_utilities import load_json

RESOURCES = {
    "GBFS 2.3": "https://sharedmobility.ch/v2/gbfs",
    "GBFS 2.1": "https://data.opentransportdata.swiss/dataset/sharedmobility/resource_permalink/gbfs.json"
}

EXCLUDED_URLS = {
    "https://sharedmobility.ch/v2/gbfs/donkey_le_locle/system_pricing_plans"
}

def run() -> DataTest:
    data_test = DataTest(name="gbfs_shared_mobility_test")
    MY_TOKEN = "opendata@sbb.ch"

    # loads both resources and checks their availability
    for key, url in RESOURCES.items():
        resource_data, size, data_test = load_json(url, data_test = data_test, key=MY_TOKEN)

        if not resource_data:
            return data_test

        # checks in GBFS 2.1 if feeds exist:
        if key == "GBFS 2.1":
            feeds = resource_data.get("data", {}).get("en", {}).get("feeds", [])

            data_test.test(
                condition=(len(feeds) > 0),
                if_false_log_failure=f"GBFS 2.1 ({url}) contains no feeds!",
                if_true_log_info=f"GBFS 2.1 discovery ok. {len(feeds)} feeds found."
            )

            # checks in the feeds if the urls exist
            for feed in feeds:
                feed_name = feed.get("name")
                feed_url = feed.get("url")

                if feed_url:
                    if feed_url in EXCLUDED_URLS:
                        continue
                    _, size, data_test = load_json(feed_url, data_test=data_test)
                    data_test.test(
                        condition=(size > 0),
                        if_false_log_failure=f"Feed ({feed_url}) has no content!",
                        if_true_log_info=f"Feed {feed_name} contains something."
                    )


        # checks in GBFS 2.3 if systems exist
        elif key == "GBFS 2.3":
            systems = resource_data.get("systems", [])

            data_test.test(
                condition=(len(systems) > 0),
                if_false_log_failure=f"GBFS 2.3 ({url}) System list is empty!",
                if_true_log_info=f"GBFS 2.3 ok. {len(systems)} systems found."
            )

            # checks in the systems if the url exist
            for system in systems:
                system_name = system.get("name")
                system_url = system.get("url")

                if system_url:
                    if system_url in EXCLUDED_URLS:
                        continue
                    system_data, size, data_test = load_json(
                        system_url,
                        data_test=data_test,
                        key=MY_TOKEN
                    )
                    data_test.test(
                        condition=(size > 0),
                        if_false_log_failure=f"System ({system_name}) has no content!",
                        if_true_log_info=f"System {system_url} contains something."
                    )
                    # checks in the systems if the feed exists
                    feeds = system_data.get("data", {}).get("en", {}).get("feeds", [])
                    for feed in feeds:
                        feed_name = feed.get("name")
                        feed_url = feed.get("url")
                        if feed_url in EXCLUDED_URLS:
                            continue
                        feed_data, size, data_test = load_json(
                            feed_url,
                            data_test=data_test,
                            key=MY_TOKEN
                        )
                        data_test.test(
                            condition=(size > 0),
                            if_false_log_failure=f"Feed {feed_name} of {system_name} is empty! URL: {feed_url}",
                            if_true_log_info=f"Feed {feed_name} of {system_name} ok ({size} bytes)."
                        )

    return data_test


if __name__ == '__main__':
    tr = run()
    print(tr)
    print(tr.to_dict())
