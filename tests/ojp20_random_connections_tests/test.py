"""Test of the OJP 2.0 API, doing a random number of OJP Trip Requests.

Requires a file config.json in folder tests/data/ojp20_random_connections_test like this:

{
  "tyk_key": "....",
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

import os
import random
import requests
from datetime import datetime as dt

from utilities.json_utilities import load_json_file
from utilities.test_utilities import DataTest

session = requests.session()
NOW = dt.now().isoformat()
module_path = os.path.abspath(__file__)

def run():
    name = "ojp20_random_connections_test"
    data_test = DataTest(name=name)
    config = load_json_file("tests/ojp20_random_connections_tests/data/config.json")
    if config is None:
        raise ValueError("config.json not found, test terminated.")
    headers = {"Authorization": f"Bearer {config.get('tyk_key')}", "Content-Type": f"application/xml; charset=utf-8"}
    stops = config['stops']
    stops_ids = list(stops.keys())
    number_of_tests = config['number_of_tests']
    warning_threshold_sec_per_test = config['warning_threshold_sec_per_test']
    count200 = 0
    t = 0.0
    for i in range(0, number_of_tests):
        time.sleep(config['sleep_time'])

        origin_ref = random.choice(stops_ids)
        while True:
            destin_ref = random.choice(stops_ids)
            if destin_ref != origin_ref:
                break

        tr = OJP_TR_TEMPLATE.strip().replace("{{timestamp}}", NOW + "+02:00")
        tr = tr.replace("{{origin_ref}}", origin_ref).replace("{{origin_name}}", stops[origin_ref])
        tr = tr.replace("{{destin_ref}}", destin_ref).replace("{{destin_name}}", stops[destin_ref])
        tr = tr.replace("{{arrdep}}", NOW[:16] + ":00Z")
        body_bytes = str(tr).encode('utf-8')
        url = "https://api.opentransportdata.swiss/ojp20"
        t0 = time.time()
        response = session.post(url, data=body_bytes, headers=headers)
        dt = time.time() - t0
        t += dt
        response_str = response.content.decode('utf-8')
        if response.status_code != 200:
            data_test.log_failure(f"Test {origin_ref}/{stops[origin_ref]}->{destin_ref}/{stops[destin_ref]} failed with status code {response.status_code}, excerpt: {response_str[:300]}...")
        else:
            count200 += 1
        #    data_test.log_info(f"Test succeeded: {stops[origin_ref]}->{stops[destin_ref]}, {len(response.content)} bytes, status={response.status_code}: {response_str[:20]}...")

    data_test.log_info(f"Performed {number_of_tests}, of which {count200} with 200 in {t:0.3f} seconds.")
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
