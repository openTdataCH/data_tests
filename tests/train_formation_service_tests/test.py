"""Test of the train formation service API.

- Load config data from CONFIG_FILE. This file must have a structure/content like this:
{
  "number_of_tests": 10,
  "connections": {
    "name": {
      "base_url": "https://api.opentransportdata.swiss/formation/v2",
      "tyk_key": "... key for tyk ..."
    }
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

"""
import random
import requests
from datetime import datetime as dt

from utilities.json_utilities import load_json_file
from utilities.test_utilities import DataTest
from utilities.ojp_utilities.easy_ojp20 import ojp20_triprequest

ENDPOINTS = ("formations_vehicle_based", "formations_stop_based", "formations_full")

NOW = dt.now().isoformat()
TEST_NAME = "train_formation_service_tests"
CONFIG_FILE = f"tests/{TEST_NAME}/data/config.json"
CONFIG = load_json_file(CONFIG_FILE)

TFS_ENABLED_OPS = {
    "33": "BLSP",
    "29": "MBC",
    "68": "OeBB",
    "72": "RhB",
    "11": "SBBP",
    "82": "SOB",
    "65": "THURBO",
    "53": "TPF",
    "44": "TRN",
    "9014": "VDBB",
    "86": "ZB"
}


def random_pair_of_stops(stops: list) -> tuple:
    origin_ref = random.choice(stops)
    while True:
        destin_ref = random.choice(stops)
        if destin_ref != origin_ref:
            return origin_ref, destin_ref


def get_ojp20_tr_first_tfs_enabled_train_leg(origin_ref: str, destin_ref: str, data_test: DataTest) -> tuple:
    """From the given OJP 2.0 TR, extracts the first op_day, TFS-enabled operator and train number it can find, or None."""
    od, op, tn = None, None, None
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
                        if od and op in TFS_ENABLED_OPS.keys() and tn:
                            return od, op, tn
    except Exception as e:
        data_test.log_warning(f"Failed to get a train from given OJP20 TR response for {origin_ref}, {destin_ref}: {e}")
    return od, op, tn


def test_tfs(conn_key, endpoint, operation_date, evu_nr, train_number, data_test):
    tyk_key = CONFIG['connections'][conn_key]['tyk_key']
    base_url = CONFIG['connections'][conn_key]['base_url']
    headers = {"Authorization": "bearer " + tyk_key, "Content-Type": 'application/octet-stream'}
    evu_short = TFS_ENABLED_OPS[evu_nr]
    url = f"""{base_url}/{endpoint}?evu={evu_short}&operationDate={operation_date}&trainNumber={train_number}"""
    response = requests.get(url, headers=headers)
    response_str = response.content.decode('utf-8')
    message = f"- TFS test {conn_key} / {endpoint}: {response.status_code} {response.reason}, {len(response.content)} bytes."
    data_test.test(response.status_code < 400, if_true_log_info=message, if_false_log_warning=message)


def run():
    data_test = DataTest(name=TEST_NAME)
    if CONFIG is None:
        raise ValueError("config.json not found, test terminated.")
    stop_ids = list(CONFIG['stops'].keys())
    conns = CONFIG['connections']
    for i in range(0, CONFIG['number_of_tests']):
        origin_ref, destin_ref = random_pair_of_stops(stop_ids)
        od, op, tn = get_ojp20_tr_first_tfs_enabled_train_leg(origin_ref, destin_ref, data_test)
        if od and op and tn:
            data_test.log_info(f"Testing {od} / {op} / {tn} now:")
            # found a "train" which is TFS enalbed; can continue now with the TFS test on it
            for endpoint in ENDPOINTS:
                for conn_key in conns.keys():
                    try:
                        test_tfs(conn_key, endpoint, od, op, tn, data_test)
                    except Exception as e:
                        data_test.log_exception(f"Failed to test {endpoint} / {conn_key}: {e}", e)

    return data_test


if __name__ == '__main__':
    tr = run()
    print(tr)
