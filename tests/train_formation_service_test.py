"""Test of the train formation service API.

Markus Meier, 2026-01-12
"""

import requests
from datetime import datetime as dt

from configuration import get_prop
from utilities.test_utilities import DataTest

ENDPOINTS = ("formations_vehicle_based", "formations_stop_based", "formations_full")



def run(config: dict = None) -> dict:
    data_test = DataTest(name="train_formation_service_test")
    key = config.get("key_train_formation_servce")
    headers = {"Authorization": "bearer " + key, "Content-Type": 'application/octet-stream'}
    evu = "SBBP"
    train_number = "556"
    operation_date = dt.now().isoformat()[:10]
    url = f"""https://api.opentransportdata.swiss/formation/v1/{ENDPOINTS[2]}?evu={evu}&operationDate={operation_date}""" + \
          f"""&trainNumber={train_number}"""
    response = requests.get(url, headers=headers)
    response_str = response.content.decode('utf-8')
    message = f"response status code: {response.status_code}, {len(response.content)} bytes"
    data_test.test(response.status_code < 400, if_true_log_info=message, if_false_log_failure=message)

    return data_test.to_dict()


if __name__ == '__main__':
    from configuration import CONFIG
    tr = run(config=CONFIG)
    print(tr)
    print(tr['logs'])
