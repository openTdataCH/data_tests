"""Utilities (classes, functions) for access to the CKAN metadata.

"""

import json
import requests

from configuration import get_prop
from utilities.string_utilities import strip_html_tags
from utilities.test_utilities import DataTest

URL_SHOW = "https://api.opentransportdata.swiss/ckan-api/package_show?id="
URL_LIST = "https://api.opentransportdata.swiss/ckan-api/package_list"


def load_ckan_package_list(data_test: DataTest = None):
    """Load and return a list of available CKAN packages (dataset, harvester, showcase); returns a list plus test report, as a tuple."""
    if data_test is None:
        data_test = DataTest(name="load_ckan_package_list")
    headers = {'Content-Type': 'application/json', 'Authorization': get_prop('key_ckan')}
    response = requests.get(URL_LIST, headers=headers)
    if response.status_code >= 400:
        data_test.log_failure(f"Loaded CKAN metadata (package_list), status_code={response.status_code}")
        return [], data_test

    json_data = json.loads(response.content.decode('utf-8'))
    if json_data.get('success')!=True or type(json_data.get('result')) != list:
        data_test.log_failure(f"CKAN metadata (package_list) does not have 'success'==True and 'result' list.")
        return [], data_test

    return json_data['result'], data_test


def load_ckan_package(package_name: str, test_report: DataTest = None) -> tuple:
    """Load and return the CKAN metadata for a given package (dataset); returns JSON data, plus size (int) nd test report, as a tuple."""
    if test_report is None:
        test_report = DataTest(name="load_ckan_package")

    headers = {'Content-Type': 'application/json', 'Authorization': get_prop('key_ckan')}

    response = requests.get(URL_SHOW + package_name, headers=headers)
    size = len(response.content)
    excerpt = strip_html_tags(response.content.decode('utf-8'))[0:200]
    message = f"Loaded CKAN metadata (package_show) for {package_name} with {len(response.content)} bytes, status_code={response.status_code}, excerpt={excerpt})"
    is_lt_400 = test_report.test(response.status_code < 400, if_false_log_failure=message)
    if not is_lt_400:
        return {}, size, test_report

    encoding = 'utf-8-sig' if response.content.startswith(b'\xef\xbb\xbf') else 'utf-8'

    json_data = json.loads(response.content.decode(encoding))
    test_report.test(json_data.get("result") is not None, if_false_log_failure="JSON data has no key 'result'.")
    test_report.test(json_data.get("success") == True, if_false_log_failure="JSON data does not have 'success==True'.")

    return json_data.get("result"), size, test_report


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
