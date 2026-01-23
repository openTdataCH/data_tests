"""Utilities (classes, functions) for access to the CKAN metadata.

"""

import json
import requests

from configuration import get_prop
from utilities.test_utilities import DataTest

URL = "https://api.opentransportdata.swiss/ckan-api/package_show?id="


def load_ckan_package(package_name: str, test_report: DataTest = None) -> tuple:
    """Load and return the CKAN metadata for a given package (dataset); returns JSON data, plus size (int) nd test report, as a tuple."""
    if test_report is None:
        test_report = DataTest(name="load_ckan_package")

    headers = {'Content-Type': 'application/json', 'Authorization': get_prop('key_ckan')}

    response = requests.get(URL + package_name, headers=headers)
    size = len(response.content)
    message = f"Loaded CKAN metadata (package_show for {package_name} with {len(response.content)} bytes, status_code={response.status_code}, excerpt={response.content[0:200]})"
    is_lt_400 = test_report.test(response.status_code < 400, if_true_log_info=message, if_false_log_failure=message)
    if not is_lt_400:
        return {}, size, test_report

    encoding = 'utf-8-sig' if response.content.startswith(b'\xef\xbb\xbf') else 'utf-8'

    json_data = json.loads(response.content.decode(encoding))
    test_report.test(json_data.get("result") is not None, if_false_log_failure="JSON data has no key 'result'.")
    test_report.test(json_data.get("success") == True, if_false_log_failure="JSON data does not have 'success==True'.")

    return json_data, size, test_report


def resource_by_identifier(package_metadata: dict, identifier: str) -> dict:
    """From a given package_metadata, get the metadata of a resource by identifier, return None if it fails"""
    if package_metadata is None or identifier is None:
        return None
    for resource in package_metadata["resources"]:
        if resource["identifier"] == identifier:
            return resource
    return None



if __name__ == '__main__':
    print("Simple test of load_ckan_package for given package ist-daten-v2")
    data, size, test_report = load_ckan_package("ist-daten-v2")
    print(test_report)
    print("Done.")
