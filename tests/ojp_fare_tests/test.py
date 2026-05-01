"""
This test checks the OJP Fare Interface. This is done by:
- creating a trip request
- extracting a trip from a trip request
- creating a fare request
- checking if the fare is a valid amount
"""

import requests
from lxml import etree
from utilities.json_utilities import load_json_file
from datetime import datetime
from utilities.ojp_utilities.easy_ojp20 import ojp10_triprequest
from utilities.test_utilities import DataTest

TEST_NAME = "ojp_fare_tests"
CONFIG_FILE = f"tests/{TEST_NAME}/data/config.json"

NS = {
    'siri': 'http://www.siri.org.uk/siri',
    'ojp': 'http://www.vdv.de/ojp'
}

FARE_OPTIONS = {
    "test1": {
        "params": ["Adult", "second", 20, None, None],
        "expected_price": "42.00"
    },
    "test2": {
        "params": ["Adult", "first", 76, None, None],
        "expected_price": "72.00"
    },
    "test3": {
        "params":["Adult", "second", 20, "HTA", "Halbtax-Abonnement"],
        "expected_price": "42.00"
    },
    "test4": {
        "params":["Adult", "first", 76, "HTA", "Halbtax-Abonnement"],
        "expected_price": "72.00"
    }
}

url_fare = "https://api.opentransportdata.swiss/ojpfare"

timestamp = datetime.now().strftime("%Y-%m-%d")

def get_fare_body(trip_snippet, passenger_category="Adult", travel_class="first", age=25, entitlement_product=None, entitlement_product_name=None):
    entitlement_xml = ""
    if entitlement_product:
        entitlement_xml = f"""      <ojp:EntitlementProducts>
                                    <ojp:EntitlementProduct>
                                        <ojp:FareAuthorityRef>ch:1:NOVA</ojp:FareAuthorityRef>
                                        <ojp:EntitlementProductRef>{entitlement_product}</ojp:EntitlementProductRef>
                                        <ojp:EntitlementProductName>{entitlement_product_name}</ojp:EntitlementProductName>
                                    </ojp:EntitlementProduct>
                                </ojp:EntitlementProducts>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<OJP xmlns:siri="http://www.siri.org.uk/siri" xmlns="http://www.siri.org.uk/siri" xmlns:ojp="http://www.vdv.de/ojp" version="1.0">
    <OJPRequest>
        <ServiceRequest>
            <RequestTimestamp>{timestamp}T11:56:11.714265</RequestTimestamp>
            <RequestorRef>OJP2NOVA</RequestorRef>
            <ojp:OJPFareRequest>
                <RequestTimestamp>{timestamp}T11:56:11.714265</RequestTimestamp>
                <ojp:TripFareRequest>
                    {trip_snippet}
                </ojp:TripFareRequest>
                <ojp:Params>
                    <ojp:FareAuthorityFilter>ch:1:NOVA</ojp:FareAuthorityFilter>
                    <ojp:PassengerCategory>{passenger_category}</ojp:PassengerCategory>
                    <ojp:TravelClass>{travel_class}</ojp:TravelClass>
                    <ojp:Traveller>
                        <ojp:Age>{age}</ojp:Age>
                        <ojp:PassengerCategory>{passenger_category}</ojp:PassengerCategory>
                        {entitlement_xml}
                    </ojp:Traveller>
                </ojp:Params>
            </ojp:OJPFareRequest>
        </ServiceRequest>
    </OJPRequest>
</OJP>"""

def run():
    data_test = DataTest(name=TEST_NAME)
    test_config = load_json_file(CONFIG_FILE)
    if test_config is None:
        raise ValueError("config.json not found, test terminated.")

    #Trip request
    status, size, trip_xml = ojp10_triprequest(
        a_bpuic="8503000",
        a_name="Zürich (Zürich)",
        b_bpuic="8509000",
        b_name="Chur (Chur)",
        departure_time_iso8601=f"{timestamp}T11:12:00.000Z",
        return_as="xml",
        data_test=data_test
    )

    if status != 200 or isinstance(trip_xml, str) and trip_xml.startswith("<xml><ERROR>"):
        data_test.log_failure(f"Trip Request failed: {status}, response: {trip_xml}")
        return data_test

    trip_element = trip_xml.find(".//ojp:Trip", NS)

    if trip_element is not None:
        etree.cleanup_namespaces(trip_element)

        trip_snippet = etree.tostring(trip_element, encoding='unicode', pretty_print=False)
        # Fare Requests
        for test_id, config in FARE_OPTIONS.items():
            params = config["params"]
            passenger_category, travel_class, age, entitlement_product, entitlement_name = params
            expected_price = config["expected_price"]

            fare_xml_body = get_fare_body(trip_snippet, *params)
            headers = {"Authorization": f"Bearer {test_config['key_ojp_fare']}", "Content-Type": "application/xml; charset=utf-8"}
            response_fare = requests.post(url_fare, data=fare_xml_body.encode('utf-8'), headers=headers)
            fare_root = etree.fromstring(response_fare.content)

            actual_price = None
            for product in fare_root.findall(".//ojp:FareProduct", NS):
                tc = product.find("ojp:TravelClass", NS)
                if tc is not None and tc.text == travel_class:
                    actual_price = product.find("ojp:Price", NS).text
                    break

            if actual_price:
                if actual_price == expected_price:
                    data_test.log_info(f"{test_id} checked successfully: {actual_price} CHF found for {travel_class} class.")
                else:
                    data_test.log_failure(f"{test_id} wrong price. Expected {expected_price}, got {actual_price} for {travel_class} class.")
            else:
                data_test.log_failure(f"{test_id} No price found for class {travel_class}")
    else:
        data_test.log_failure("No Trip element found")
    return data_test

if __name__ == '__main__':
    tr = run()
    print(tr.to_dict())