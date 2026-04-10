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
import requests
from datetime import datetime as dt
from jsonschema import validate, ValidationError, SchemaError

from utilities.file_and_path_utilities import get_path
from utilities.json_utilities import load_json_file
from utilities.ojp_utilities.easy_ojp20 import ojp20_triprequest
from utilities.test_utilities import DataTest
from utilities.xml_utilities import easy_xml

session = requests.session()
NOW = dt.now().isoformat()
TEST_NAME = "ojp20_tr_random_validated_tests"
CONN_LOG_FILE = f"tests/{TEST_NAME}/data/{TEST_NAME}_log.txt"
CONFIG_FILE = f"tests/{TEST_NAME}/data/config.json"
SCHEMA_FILE = f"tests/{TEST_NAME}/ojp20_tr_schema_depth_to_legs.json"
json_schema = load_json_file(get_path(SCHEMA_FILE))


def _timestamp():
    return dt.now().isoformat()[:23]


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
            time.sleep(config['sleep_time'])
            origin_ref = random.choice(stops_ids)
            while True:
                destin_ref = random.choice(stops_ids)
                if destin_ref != origin_ref:
                    break
            t0 = time.time()
            status, xmlbytes = ojp20_triprequest(origin_ref, destin_ref, return_as='dict', data_test=data_test)
            delta_t = time.time() - t0
            t += delta_t
            conn_text = f"{origin_ref} {stops[origin_ref]:30}-> {destin_ref} {stops[destin_ref]:30}"

            conn_log.write(f'{_timestamp()} {conn_text}: {delta_t:.3f} sec.,{len(xmlbytes):>9} bytes, status={status}, excerpt={xmlbytes[:30]}...\n')

            if status != 200:
                data_test.log_failure(f"OJP2.0 TR with {conn_text} failed with status code {status}, excerpt: {xmlbytes[:30]}...")
            else:
                count200 += 1
                try:
                    data = easy_xml.xml_to_dict(xmlbytes)
                    jsondata = json.dumps(data, ensure_ascii=False, indent=2)
                    validate(instance=data, schema=json_schema)
                    count_valid += 1
                except ValidationError as e:
                    data_test.log_warning(f"Validation error: {str(e.message)}")
                    count_invalid += 1
                except SchemaError as e:
                    data_test.log_exception(f"Invalid schema: {str(e)}", e)
                except Exception as e:
                    data_test.log_failure(f"OJP2.0 TR with {conn_text} processing failed with {str(e)}, excerpt: {xmlbytes[:30]}...")

        data_test.log_info(f"Performed {number_of_tests} OJP2.0 TR: {count200} ok (status 200), {count_valid} valid, {count_invalid} invalid, average {t/number_of_tests:0.3f} seconds.")
        if t / number_of_tests > warning_threshold_sec_per_test:
            data_test.log_warning(f"Test time of {t/number_of_tests:.3f} sec. exceded {warning_threshold_sec_per_test:.3f} sec. threshold.")

    return data_test


OJP_TR_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<OJP xmlns="http://www.vdv.de/ojp" xmlns:siri="http://www.siri.org.uk/siri" version="2.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.vdv.de/ojp OJP_changes_for_v1.1/OJP.xsd">
    <OJPRequest>
        <siri:ServiceRequest>
            <siri:RequestTimestamp>{{timestamp}}</siri:RequestTimestamp>
            <siri:RequestorRef>SKI+/data_tests/ojp20_random_connections_tests</siri:RequestorRef>
            <OJPTripRequest>
                <siri:RequestTimestamp>{{timestamp}}</siri:RequestTimestamp>
                <Origin>
                    <PlaceRef>
                        <siri:StopPointRef>{{origin_ref}}</siri:StopPointRef>
                        <Name>
                            <Text>{{origin_name}}</Text>
                        </Name>
                    </PlaceRef>
                    <DepArrTime>{{arrdep}}</DepArrTime>
                </Origin>
                <Destination>
                    <PlaceRef>
                        <siri:StopPointRef>{{destin_ref}}</siri:StopPointRef>
                        <Name>
                            <Text>{{destin_name}}</Text>
                        </Name>
                    </PlaceRef>
                </Destination>
                <Params>
                    <NumberOfResults>5</NumberOfResults>
                    <IncludeTrackSections>false</IncludeTrackSections>
                    <IncludeLegProjection>true</IncludeLegProjection>
                    <IncludeTurnDescription>false</IncludeTurnDescription>
                    <IncludeIntermediateStops>false</IncludeIntermediateStops>
                </Params>
            </OJPTripRequest>
        </siri:ServiceRequest>
    </OJPRequest>
</OJP>"""



if __name__ == '__main__':
    tr = run()
    print(tr)
