"""
This test checks the OJP Fare Interface. This is done by:
- creating a trip request
- extracting a trip from a trip request
- creating a fare request
- checking if the fare is a valid amount
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from utilities.test_utilities import DataTest
import configuration

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
        "params":["Child", "second", 14, None, None],
        "expected_price": "42.00"
    },
    "test4": {
        "params":["Child", "first", 15, None, None],
        "expected_price": "72.00"
    },
    "test5": {
        "params":["Adult", "second", 20, None, "HTA"],
        "expected_price": "42.00"
    },
    "test6": {
        "params":["Adult", "first", 76, None, "HTA"],
        "expected_price": "72.00"
    }
}

url_trip = "https://skiplus-ojp-nova-prod.sbb-cloud.net/ojp2023"
url_fare = "https://skiplus-ojp-fare.api.sbb.ch/ojp2023"

timestamp = datetime.now().strftime("%Y-%m-%d")

def get_fare_body(trip_snippet, passenger_category="Adult", travel_class="first", age=25, entitlement_product=None, entitlement_product_name=None):
    entitlement_xml = ""
    if entitlement_product:
        entitlement_xml = f"""
                                <ojp:EntitlementProducts>
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
            <RequestTimestamp>{timestamp}</RequestTimestamp>
            <RequestorRef>OJP2NOVA</RequestorRef>
            <ojp:OJPFareRequest>
                <RequestTimestamp>{timestamp}</RequestTimestamp>
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


def get_access_token():
    """Gets OAuth2 Access Token"""
    token_url = "https://login.microsoftonline.com/2cda5d11-f0ac-46b3-967d-af1b2e1bd01a/oauth2/v2.0/token"
    payload = {
        "grant_type": configuration.get_prop("grant_type"),
        "client_id": configuration.get_prop("client_id"),
        "client_secret": configuration.get_prop("client_secret"),
        "scope": configuration.get_prop("scope")
    }
    response = requests.post(token_url, data=payload)
    response.raise_for_status()
    return response.json().get("access_token")

def run():
    data_test = DataTest(name="ojp_fare_test")
    token = get_access_token()

    headers = {
        "Content-Type": "application/xml",
        "Authorization": f"Bearer {token}",
        "Accept": "application/xml"
    }

    #Trip request
    try:
        trip_xml_body = f"""
            <OJP xmlns="http://www.siri.org.uk/siri" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:ojp="http://www.vdv.de/ojp" xsi:schemaLocation="http://www.siri.org.uk/siri ../ojp-xsd-v1.0/OJP.xsd" version="1.0">
              <OJPRequest>
                <ServiceRequest>
                  <RequestorRef>OJP SDK v1.0</RequestorRef>
                  <RequestTimestamp>{timestamp}T11:12:00.000Z</RequestTimestamp>
                  <ojp:OJPTripRequest>
                    <RequestTimestamp>{timestamp}T11:12:00.000Z</RequestTimestamp>
                    <ojp:Origin>
                      <ojp:PlaceRef>
                        <StopPointRef>8503000</StopPointRef>
                        <ojp:LocationName>
                          <ojp:Text>Zürich (Zürich)</ojp:Text>
                        </ojp:LocationName>
                      </ojp:PlaceRef>
                    </ojp:Origin>
                    <ojp:Destination>
                      <ojp:PlaceRef>
                        <StopPointRef>8509000</StopPointRef>
                        <ojp:LocationName>
                          <ojp:Text>Chur (Chur)</ojp:Text>
                        </ojp:LocationName>
                      </ojp:PlaceRef>
                    </ojp:Destination>
                    <ojp:Params>
                      <ojp:NumberOfResultsAfter>5</ojp:NumberOfResultsAfter>
                      <ojp:IncludeTrackSections>false</ojp:IncludeTrackSections>
                      <ojp:IncludeLegProjection>false</ojp:IncludeLegProjection>
                      <ojp:IncludeTurnDescription>false</ojp:IncludeTurnDescription>
                      <ojp:IncludeIntermediateStops>true</ojp:IncludeIntermediateStops>
                    </ojp:Params>
                  </ojp:OJPTripRequest>
                </ServiceRequest>
              </OJPRequest>
            </OJP>"""
        response = requests.post(url_trip, data=trip_xml_body.encode('utf-8'), headers=headers)

        if response.status_code != 200:
            data_test.log_failure(f"Trip Request failed: {response.status_code} - Response: {response.text}")
            return data_test
        root = ET.fromstring(response.content)
        trip_element = root.find(".//ojp:Trip", NS)

        if not data_test.test(condition=(trip_element is not None), if_false_log_failure="No Trip found"):
            return data_test

        trip_snippet = ET.tostring(trip_element, encoding='unicode')

        # Fare Requests
        for test_id, config in FARE_OPTIONS.items():
            params = config["params"]
            passenger_category, travel_class, age, entitlement_product, entitlement_name = params
            expected_price = config["expected_price"]

            fare_xml_body = get_fare_body(trip_snippet, *params)
            response_fare = requests.post(url_fare, data=fare_xml_body.encode('utf-8'), headers=headers)
            fare_root = ET.fromstring(response_fare.content)

            actual_price = None
            for product in fare_root.findall(".//ojp:FareProduct", NS):
                tc = product.find("ojp:TravelClass", NS)
                if tc is not None and tc.text == travel_class:
                    actual_price = product.find("ojp:Price", NS).text
                    break

            if actual_price:
                if actual_price == expected_price:
                    data_test.log_info(f"{test_id} checked successfully: {actual_price} CHF found for {travel_class}.")
                else:
                    data_test.log_failure(f"{test_id} wrong price. Expected {expected_price}, got {actual_price} for {travel_class} class.")
            else:
                data_test.log_failure(f"{test_id} No price found for class {travel_class}")

    except Exception as e:
        data_test.log_exception(f"Error when executing OJP Test {e}.", e)

    return data_test

if __name__ == '__main__':
    tr = run()
    print(tr.to_dict())