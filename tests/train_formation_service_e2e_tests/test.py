"""End-to-end testing of the train formation service API.

The test is designed to run a best-possible, reproducible list of trains.

The test works as follows:
- load trips_file, a geojson file with at least number_of_tests trips from A to B, train stations, 100+ km apart.
- for each trip A-B, do a OJP TR and take the first train that is one of the allowed operators.
- for the thus given operator, train number and operation day (today), test all given TFS endpoints (connections)
- for each endpoint, do a (basic) validation to determine whether the response is valid or not.
- the entire test gives warnings, failures or errors based on given thresholds.

Thie config.json file must have the following structure / nodes:
{
  "number_of_tests": 100,
  "sleep_seconds": 2.0,
  "trips_file": "trips200.geojson",
  "thresholds_warn_percents": {
      "v1/full": 20,
       "v1/stop": 20,
       "v1/vehi": 20, ...
  },
  "fail_to_warn_ratio": 2.0,
  "connections": {
    "v1/full": {
      "format": "v1/full",
      "url": "https://api.opentransportdata.swiss/formation/v1/formations_full",
      "tyk_key": "... the key ..."
    }, ...
  },
  "tfs_enabled_operators": {
    "33": "BLSP", ...
  }
}

"""

import time

import json
from collections import defaultdict

import requests
from datetime import datetime as dt

from utilities.json_utilities import load_json_file
from utilities.ojp_utilities.easy_ojp20 import ojp20_triprequest
from utilities.string_utilities import flatten
from utilities.test_utilities import DataTest

ENDPOINTS = ("formations_vehicle_based", "formations_stop_based", "formations_full")

NOW = dt.now().isoformat()
TEST_NAME = "train_formation_service_e2e_tests"


def get_ojp20_tr_first_tfs_enabled_train_leg(config: dict, origin_ref: str, destin_ref: str, data_test: DataTest) -> tuple:
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
                        if od and op in config.get('tfs_enabled_operators').keys() and tn:
                            return od, op, tn
    except Exception as e:
        # this may happen, probably not a problem -- just log it as 'info' and ignore it otherwise.
        data_test.log_info(f"Failed to get a train from given OJP20 TR response for {origin_ref}, {destin_ref}: {e}.")
    return None, None, None


def obtain_train(index, config: dict, trip: dict, data_test: DataTest):
    trip_props = trip['properties']
    od, op, tn = get_ojp20_tr_first_tfs_enabled_train_leg(config, trip_props['origin_number'], trip_props['destin_number'], data_test)
    if od and op and tn:
        data_test.log_info(f"#{index}: Found train {od, op, tn} for trip {trip_props['origin_name']} to {trip_props['destin_name']}.")
    else:
        data_test.log_info(f"#{index}: Found no train for trip {trip_props['origin_name']} to {trip_props['destin_name']}.")
    return od, op, tn


def load_configs(data_test: DataTest) -> tuple:
    """Load the configuration files."""
    config = load_json_file(f"tests/{TEST_NAME}/data/config.json")
    trips_geojson = load_json_file(f"tests/{TEST_NAME}/data/{config['trips_file']}")
    trips = trips_geojson.get('features')
    data_test.log_info(f"found {len(trips)} trips.")
    return config, trips


def validate_v1_and_v2(config, conn_key, resp):
    """Validations of the TFS V1 and V2 formats; checks the top level nodes, based on the type.
    The 'format' must start with v and end will full/vehi/stop, respectively, else, no validations are done."""
    format = config['connections'][conn_key]['format']
    msg = ""
    if format.startswith('v'):
        # all:
        msg += "" if resp.get('trainMetaInformation') and len(list(resp.get('trainMetaInformation').keys())) >= 3 else "Missing or incomplete 'trainMetaInformation' node. "
        msg += "" if resp.get('journeyMetaInformation') and len(list(resp.get('journeyMetaInformation').keys())) >= 2 else "Missing or incomplete 'journeyMetaInformation' node. "
        msg += "" if resp.get('vehicleJourneyType') else "Missing 'vehicleJourneyType' node. "
        msg += "" if resp.get('lastUpdate') else "Missing 'lastUpdate' node. "

        # variants full and vehicle-based:
        if format.endswith('full') or format.endswith('vehi'):
            msg += "" if resp.get('formations') and len(resp.get('formations')) > 0 else "Missing or empty 'formations' node. "
            msg += "" if resp.get('relationships') and len(resp.get('relationships')) > 0 else "Missing or empty 'relationships' node. "

        # variants full and stop-based:
        if format.endswith('full') or format.endswith('stop'):
            msg += "" if resp.get('formationsAtScheduledStops') and len(resp.get('formationsAtScheduledStops')) > 0 else "Missing or empty 'formationsAtScheduledStops' node. "

    msg = None if msg.strip() == '' else msg
    return msg


def do_validition(config, conn_key, response, data_test):
    response_str = response.content.decode('utf-8')
    message = f"TFS test {conn_key:10}: {response.status_code} {response.reason}, {len(response.content)} bytes"
    if response.status_code < 400 and response_str.startswith('{'):  # this is a rough, preliminary validation
        response_json = json.loads(response_str)
        denial_message = validate_v1_and_v2(config, conn_key, response_json)
        if denial_message:
            data_test.log_info(f"⛔{message}: {denial_message}")
            return 0
        else:
            data_test.log_info(f"✅{message}: VALID")
            return 1
    else:
        excerpt = flatten(response_str[:100])
        data_test.log_info(f"⛔{message}, excerpt: {excerpt}{'...' if len(excerpt) > 100 else '.'}")
        return 0


def test_tfs(config, conn_key, operation_date, evu_nr, train_number, data_test):
    global previews_bytes_count
    tyk_key = config['connections'][conn_key]['tyk_key']
    url = config['connections'][conn_key]['url']
    headers = {"Authorization": "bearer " + tyk_key, "Content-Type": 'application/octet-stream'}
    evu_short = config['tfs_enabled_operators'][evu_nr]
    url = f"""{url}?evu={evu_short}&operationDate={operation_date}&trainNumber={train_number}"""
    response = requests.get(url, headers=headers)

    time.sleep(config['sleep_seconds'])
    return do_validition(config, conn_key, response, data_test)


def check_thresholds(counts, config, data_test: DataTest):
    f2w_ratio = config['fail_to_warn_ratio']
    n = config['number_of_tests']
    for key, twp in config['thresholds_warn_percents'].items():
        if counts.get(key):
            threashold_warn, threashold_fail = round(0.01 * (100.0 - twp) * n), round(0.01 * (100.0 - twp * f2w_ratio) * n)
            if counts[key] < threashold_fail:
                data_test.log_failure(f"Only {counts[key]} of {n} total succeeded for {key}, is below failure threshold {threashold_fail}.")
            elif counts[key] < threashold_warn:
                data_test.log_warning(f"Only {counts[key]} of {n} total succeeded for {key}, is below warning threshold {threashold_warn}.")


def show_statistics_one_bar(key: str, percentage: int,  data_test: DataTest):
    data_test.log_info(f"Valid {'■' * percentage}{'□' * (100 - percentage)} {percentage} % for {key}.")


def show_statistics(counts, config, data_test: DataTest):
    data_test.log_info("Statistics:")
    for key in [k for k in counts.keys() if k.startswith('v')] + ['total']:
        percentage = round(100.0 * counts[key] / config['number_of_tests'])
        show_statistics_one_bar(key, percentage, data_test)


def run():
    data_test = DataTest(name=TEST_NAME)
    counts = defaultdict(int)
    try:
        config, trips = load_configs(data_test)
        counts['number_of_tests'] = config['number_of_tests']
        trip_i = 0
        while counts['total'] < config['number_of_tests']:
            trip = trips[trip_i]
            od, op, tn = obtain_train(trip_i, config, trip, data_test)
            if od and op and tn:
                for conn_key in config['connections'].keys():
                    counts[conn_key] += test_tfs(config, conn_key, od, op, tn, data_test)
                counts['total'] += 1
            else:
                counts['trains_not_found'] += 1

            trip_i += 1

        show_statistics(counts, config, data_test)
        check_thresholds(counts, config, data_test)

    except Exception as e:
        data_test.log_exception(f"Failed test: {str(e)}")

    return data_test


if __name__ == '__main__':
    tr = run()
    print(tr)
