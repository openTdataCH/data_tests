"""Test of the OJP 2.0 API, doing a random number of OJP Trip Requests.

Requires a file config.json in folder tests/data/ojp20_random_connections_test like this:

{
  "number_of_tests": 20,
  "sleep_time": 0.2,
  "warning_threshold_sec_per_test": 1.0,
  "stops": {
    "8503000": "Zürich HB",
    "8506000": "Winterthur",
    .... some more stops to test
  }
}
"""


import time

import json
import random
from datetime import datetime as dt
from jsonschema import validate, ValidationError, SchemaError

from utilities.file_and_path_utilities import get_path
from utilities.json_utilities import load_json_file
from utilities.ojp_utilities.easy_ojp20 import ojp20_triprequest
from utilities.test_utilities import DataTest

NOW = dt.now().isoformat()
TEST_NAME = "ojp20_tr_random_validated_tests"
CONN_LOG_FILE = f"tests/{TEST_NAME}/data/{TEST_NAME}_log.txt"
CONFIG_FILE = f"tests/{TEST_NAME}/data/config.json"
SCHEMA_FILE = f"tests/{TEST_NAME}/ojp20_tr_schema_depth_to_legs.json"
DUMP_FILE = f"tests/{TEST_NAME}/data/dumps/dump$$.txt"
json_schema = load_json_file(get_path(SCHEMA_FILE))


def _timestamp():
    return dt.now().isoformat()[:23]


def _dump_to_file(object, **kwargs):
    s = dt.now().isoformat()[:22].replace(":", "-")
    for k, v in kwargs.items():
        s += f"_{str(k)}_{str(v).replace(' ', '_')}"
    with open(get_path(DUMP_FILE.replace('$$', s)), "w", encoding='utf-8-sig') as f:
        f.write(object)


def run():
    data_test = DataTest(name=TEST_NAME)
    config = load_json_file(CONFIG_FILE)
    if config is None:
        raise ValueError("config.json not found, test terminated.")
    stops = config['stops']
    stops_ids = list(stops.keys())
    number_of_tests = config['number_of_tests']
    warning_threshold_sec_per_test = config['warning_threshold_sec_per_test']
    count200, count_valid, count_invalid = 0, 0, 0
    t = 0.0
    with open(get_path(CONN_LOG_FILE), mode='a', encoding='utf-8') as conn_log:
        conn_log.write(f"{'_'*200}\n{_timestamp()} Running data_test '{TEST_NAME}', {number_of_tests} random TR connections:\n")
        for i in range(0, number_of_tests):
            try:
                time.sleep(config['sleep_time'])
                origin_ref = random.choice(stops_ids)
                while True:
                    destin_ref = random.choice(stops_ids)
                    if destin_ref != origin_ref:
                        break
                t0 = time.time()
                status, size, resp_dict = ojp20_triprequest(origin_ref, destin_ref, return_as='dict', data_test=data_test)
                delta_t = time.time() - t0
                t += delta_t
                conn_text = f"{origin_ref} {str(stops[origin_ref]):30}-> {destin_ref} {str(stops[destin_ref]):30}"
                resp_str = str(resp_dict)
                resp_excp = resp_str[:30]

                conn_log.write(f'{_timestamp()} {conn_text}: {delta_t:.3f} sec.,{size:>9} bytes, status={status}, excerpt={resp_excp}...\n')

                if status != 200 or resp_dict.get('ERROR') is not None:
                    data_test.log_failure(f"OJP2.0 TR with {conn_text} failed with status code {status}, excerpt: {resp_excp}...")
                elif "TRIP_NOTRIPFOUND" in resp_str:
                    data_test.log_warning(f"OJP2.0 TR with {conn_text} got a TRIP_NOTRIPFOUND response.")
                else:
                    count200 += 1
                    jsondata = ""
                    try:
                        jsondata = json.dumps(resp_dict, ensure_ascii=False, indent=2)
                        validate(instance=resp_dict, schema=json_schema)
                    except ValidationError as e:
                        msg = str(e.message)
                        if len(msg) > 100:
                            msg = msg[:50] + "..." + msg[-50:]
                        data_test.log_warning(f"Validation error: {msg}")
                        _dump_to_file(jsondata, status=status, case="valerr")
                        count_invalid += 1
                    except SchemaError as e:
                        data_test.log_warning(f"Invalid schema: {str(e)}", e)
                    except Exception as e:
                        data_test.log_warning(f"OJP2.0 TR with {conn_text} processing failed with {str(e)}, excerpt: {resp_excp}...")
                        _dump_to_file(jsondata, status=status, case="exc")
            except Exception as e:
                data_test.log_exception(f'Test {i} failed with Exception {str(e)}', e)

        data_test.log_info(f"Performed {number_of_tests} OJP2.0 TR: {count200} ok (status 200), {count_valid} valid, {count_invalid} invalid, average {t/number_of_tests:0.3f} seconds.")
        if t / number_of_tests > warning_threshold_sec_per_test:
            data_test.log_warning(f"Test time of {t/number_of_tests:.3f} sec. exceded {warning_threshold_sec_per_test:.3f} sec. threshold.")

    return data_test


if __name__ == '__main__':
    tr = run()
    print(tr)
