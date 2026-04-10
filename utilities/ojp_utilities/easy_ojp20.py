"""Provides an easy access to the OJP 2.0 API.

Provides:
- trip_request: For given stations A and B, and given departure time, issues an OJP 2.0 TripRquest.
  - Parses the response and does simple quality checks.
  - returns either the full response, or some of the response as a simple JSON structure.

"""
import json
from zoneinfo import ZoneInfo

import requests
from datetime import datetime as dt
from lxml import etree

from configuration import get_prop
from utilities.service_points_utilities.easy_sp import get_service_point
from utilities.test_utilities import DataTest
from utilities.xml_utilities.easy_xml import xml_to_dict
from utilities.xml_utilities.xml_various_utilities import prettify_xml_bytes

from jsonschema import validate, ValidationError, SchemaError


session = requests.session()
headers = {"Authorization": f"Bearer {get_prop('key_ojp20')}", "Content-Type": "application/xml; charset=utf-8"}


def _now_iso8601():
    return dt.now(tz=ZoneInfo("Europe/Berlin")).isoformat()


def ojp20_triprequest(a_bpuic: str, b_bpuic: str, departure_time_iso8601 = _now_iso8601(), return_as = "str", data_test: DataTest = None) -> tuple:
    """A simple access to the OJP 2.0 TripRquest, with A and B (bpuic), optional departure time.
    Depending on "return_as", returns a bytes response ("bytes"), a XML str ("str", default), or a lxml _Element object ("xml", "lxml") or dict ("dict").
    Return HTML status code and the desired object, or an error message if not 200."""
    now_iso8601 = _now_iso8601()
    a_name = get_service_point('number', a_bpuic)['designationOfficial']
    b_name = get_service_point('number', b_bpuic)['designationOfficial']
    tr = OJP_TR_TEMPLATE.strip().replace("{{timestamp}}", now_iso8601)
    tr = tr.replace("{{origin_ref}}", str(a_bpuic)).replace("{{origin_name}}", a_name)
    tr = tr.replace("{{destin_ref}}", str(b_bpuic)).replace("{{destin_name}}", b_name)
    tr = tr.replace("{{arrdep}}", departure_time_iso8601)
    body_bytes = str(tr).encode('utf-8')
    url = "https://api.opentransportdata.swiss/ojp20"
    response = session.post(url, data=body_bytes, headers=headers)
    if response.status_code != 200:
        if data_test:
            data_test.log_failure(f"ojp20 TR returned {response.status_code}")
    else:
        return response.status_code, response.text
    if return_as.lower() == "bytes":
        return response.status_code, response.content
    response_str = response.content.decode('utf-8')
    if return_as.lower().endswith('xml'):
        return response.status_code, etree.XML(response.content)
    if return_as.lower().endswith('dict'):
        return response.status_code, xml_to_dict(response.content)
    return response.status_code, response_str


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
    print(f"{__file__} - simple tests")
    a, b = '8507000', '8503000'
    print(f"OJP 2.0 TR {get_service_point('number', a)['designationOfficial']} -> {get_service_point('number', b)['designationOfficial']} -- saving responses to files in ./data folder.")

    status, xml_bytes = ojp20_triprequest(a, b, return_as='bytes')
    print(f"Response with {status} status code, type={type(xml_bytes)}, {len(str(xml_bytes))} bytes.")
    open("data/ojp20_tr_raw.xml", mode='wb').write(xml_bytes)
    open("data/ojp20_tr_prettified.xml", encoding='utf-8-sig', mode='w').write(prettify_xml_bytes(xml_bytes))

    xml_dict = xml_to_dict(xml_bytes)
    open("data/ojp20_tr.json", encoding='utf-8-sig', mode='w').write(json.dumps(xml_dict, ensure_ascii=False, indent=2))

    print("Done.")

