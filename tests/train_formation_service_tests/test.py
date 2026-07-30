"""Test of the train formation service API.

- Load config data from CONFIG_FILE. This file must have a structure/content like this:
{
  "number_of_tests": 10,
  "thresholds_for_non_200_tests": {
    "warning": 3,
    "failure": 10
  },
  "connections": {
    "name": {
      "base_url": "https://api.opentransportdata.swiss/formation/v2",
      "tyk_key": "... key for tyk ..."
    }
    ...
  },
  "tfs_enabled_operators": {
    "33": "BLSP",
    ...
  },
  "stops": {
    "8500010": "Basel SBB",
    "8500207": "Solothurn",
    ...
}

- Based on a list of train stations, it chooses randomly stations A to B and calls OJP TR for those.

- If the response is valid and contains a train leg for a TFS-enabled operator, then call the given TFS connections.
    - Call the three ENDPOINTS on each connection
    - do logging and statistics
- based on the thresholds_for_non_200_tests, switch the level to "info", "warn" or "failure".

"""
import random
import requests
from datetime import datetime as dt

from utilities.json_utilities import load_json_file
from utilities.string_utilities import flatten, strip_html_tags
from utilities.test_utilities import DataTest
from utilities.ojp_utilities.easy_ojp20 import ojp20_triprequest
from utilities.service_points_utilities.easy_sp import sp_name

ENDPOINTS = ("formations_vehicle_based", "formations_stop_based", "formations_full")

NOW = dt.now().isoformat()
TEST_NAME = "train_formation_service_tests"

CONFIG_FILE = f"tests/{TEST_NAME}/data/config.json"
CONFIG = load_json_file(CONFIG_FILE)
NUMBER_OF_TESTS = CONFIG['number_of_tests']
THRESHOLDS_FOR_NON_200_TESTS = CONFIG['thresholds_for_non_200_tests']
TFS_ENABLED_OPERATORS = CONFIG['tfs_enabled_operators']


def random_pair_of_stops(stops: list) -> tuple:
    origin_ref = random.choice(stops)
    while True:
        destin_ref = random.choice(stops)
        if destin_ref != origin_ref:
            return origin_ref, destin_ref


def get_ojp20_tr_first_tfs_enabled_train_leg(origin_ref: str, destin_ref: str, data_test: DataTest) -> tuple:
    """From the given OJP 2.0 TR, extracts the first op_day, TFS-enabled operator and train number it can find, or None."""
    try:
        status, size, ojpdict = ojp20_triprequest(origin_ref, destin_ref, return_as='dict')
        trips = ojpdict['OJP']['OJPResponse']['siri:ServiceDelivery']['OJPTripDelivery']['TripResult']
        for trip in trips:
            legs = trip['Trip']['Leg']
            if type(legs) is dict:
                legs = [legs]
            for leg in legs:
                if leg.get('TimedLeg'):
                    service = leg['TimedLeg'].get('Service')
                    if service and service['Mode'].get('PtMode') == 'rail':
                        od = service.get('OperatingDayRef')
                        tn = service.get('TrainNumber')
                        op = service.get('siri:OperatorRef')
                        op = str(op).replace("ojp:", "") if op is not None else None  # strip new prefix as of July 2026
                        if od and op in TFS_ENABLED_OPERATORS.keys() and tn:
                            return od, op, tn
    except Exception as e:
        # this may happen, probably not a problem -- just log it as 'info' and ignore it otherwise.
        data_test.log_info(f"Failed to get a train from given OJP20 TR response for {origin_ref}, {destin_ref}: {e}.")
    return None, None, None


previews_bytes_count = 0

def test_tfs(conn_key, endpoint, operation_date, evu_nr, train_number, data_test, is_first = None) -> int:
    global previews_bytes_count
    tyk_key = CONFIG['connections'][conn_key]['tyk_key']
    base_url = CONFIG['connections'][conn_key]['base_url']
    headers = {"Authorization": "bearer " + tyk_key, "Content-Type": 'application/octet-stream'}
    evu_short = TFS_ENABLED_OPERATORS[evu_nr]
    url = f"""{base_url}/{endpoint}?evu={evu_short}&operationDate={operation_date}&trainNumber={train_number}"""
    response = requests.get(url, headers=headers)
    response_str = response.content.decode('utf-8')
    n_bytes = len(response.content)
    diff = 0 if is_first else n_bytes - previews_bytes_count
    diff_message = f", diff: {diff} bytes" if diff != 0 else ""
    previews_bytes_count = n_bytes
    message = f"TFS test {conn_key} / {endpoint}: {response.status_code} {response.reason}, {n_bytes} bytes{diff_message}"
    if response.status_code < 400:
        data_test.log_info(f"✅{message}.")
        return 0
    else:
        excerpt = flatten(response_str[:100])
        data_test.log_info(f"⛔{message}, excerpt: {excerpt}{'...' if len(excerpt) > 100 else '.'}")
        return 1


def run():
    data_test = DataTest(name=TEST_NAME)
    if CONFIG is None:
        raise ValueError("config.json not found, test terminated.")
    stop_ids = list(CONFIG['stops'].keys())
    conns = CONFIG['connections']
    remaining_attempts = 5 * NUMBER_OF_TESTS  # to limit the number of attempts at OJP
    count_400plus = 0
    for i in range(0, NUMBER_OF_TESTS):
        od, op, tn = None, None, None
        while tn is None:
            if remaining_attempts <= 0:
                data_test.log_warning(f"Reached limit of OJP TR calls.")
                break
            remaining_attempts = remaining_attempts - 1
            origin_ref, destin_ref = random_pair_of_stops(stop_ids)
            od, op, tn = get_ojp20_tr_first_tfs_enabled_train_leg(origin_ref, destin_ref, data_test)

        if tn and op and od:
            data_test.log_info(f"Testing op. day={od}, operator={op}/{TFS_ENABLED_OPERATORS[op]}, trainnumber={tn} ({origin_ref}/{sp_name(origin_ref)}->{destin_ref}/{sp_name(destin_ref)}):")
            # found a "train" which is TFS enalbed; can continue now with the TFS test on it
            for endpoint in ENDPOINTS:
                is_first = True
                for conn_key in conns.keys():
                    try:
                        count_400plus += test_tfs(conn_key, endpoint, od, op, tn, data_test, is_first = is_first)
                    except Exception as e:
                        count_400plus += data_test.log_exception(f"Failed to test {endpoint} / {conn_key}: {e}", e)
                    is_first = False
    if count_400plus > THRESHOLDS_FOR_NON_200_TESTS['failure']:
        data_test.log_failure(f"{count_400plus} tests with 400+ code exceeds threshold {THRESHOLDS_FOR_NON_200_TESTS['failure']} --> FAILURE.")
    elif count_400plus > THRESHOLDS_FOR_NON_200_TESTS['warning']:
        data_test.log_warning(f"{count_400plus} tests with 400+ code exceeds threshold {THRESHOLDS_FOR_NON_200_TESTS['warning']} --> WARNING.")
    else:
        data_test.log_info(f"{count_400plus} tests with 400+ is within thresholds {THRESHOLDS_FOR_NON_200_TESTS}, all well.")

    return data_test


if __name__ == '__main__':
    tr = run()
    print(tr)
