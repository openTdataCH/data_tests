"""Provides an easy access to the OJP 2.0 API.

Provides:
- trip_request: For given stations A and B, and given departure time, issues an OJP 2.0 TripRquest.
  - Parses the response and does simple quality checks.
  - returns either the full response, or some of the response as a simple JSON structure.

"""
from zoneinfo import ZoneInfo

import json
import requests
from datetime import datetime as dt
from lxml import etree

from configuration import get_prop
from utilities.service_points_utilities.easy_sp import get_service_point
from utilities.test_utilities import DataTest
from utilities.xml_utilities.easy_xml import xml_to_dict
from utilities.xml_utilities.xml_various_utilities import prettify_xml_bytes
from utilities.string_utilities import strip_html_tags

session = requests.session()
headers = {"Authorization": f"Bearer {get_prop('key_ojp20')}", "Content-Type": "application/xml; charset=utf-8"}
headers_ojp10 = {"Authorization": f"Bearer {get_prop('key_ojp10')}", "Content-Type": "application/xml; charset=utf-8"}

OJP1_TR_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<OJP xmlns="http://www.siri.org.uk/siri" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:ojp="http://www.vdv.de/ojp" xsi:schemaLocation="http://www.siri.org.uk/siri ../ojp-xsd-v1.0/OJP.xsd" version="1.0">
  <OJPRequest>
    <ServiceRequest>
      <RequestorRef>SKI+/data_tests/ojp20_random_connections_tests</RequestorRef>
      <RequestTimestamp>{{timestamp}}</RequestTimestamp>
      <ojp:OJPTripRequest>
        <RequestTimestamp>{{timestamp}}</RequestTimestamp>
        <ojp:Origin>
          <ojp:PlaceRef>
            <StopPointRef>{{origin_ref}}</StopPointRef>
            <ojp:LocationName>
              <ojp:Text>{{origin_name}}</ojp:Text>
            </ojp:LocationName>
          </ojp:PlaceRef>
        </ojp:Origin>
        <ojp:Destination>
          <ojp:PlaceRef>
            <StopPointRef>{{destin_ref}}</StopPointRef>
            <ojp:LocationName>
              <ojp:Text>{{destin_name}}</ojp:Text>
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

def _now_iso8601():
    return dt.now(tz=ZoneInfo("Europe/Berlin")).isoformat()


def _sp_name_for_bpuic(bpuic: str):
    sp = get_service_point('number', bpuic)
    if sp is None:
        raise ValueError(f"No service point known for BPUIC {bpuic}.")
    return strip_html_tags(sp.get('designationOfficial'))

def ojp_trip_request(url: str, a_bpuic: str, a_name: str, b_bpuic: str, b_name: str, departure_time_iso8601 = _now_iso8601(), return_as = "str", ojp_tr_template = OJP_TR_TEMPLATE, data_test: DataTest = None, headers=headers):
    now_iso8601 = _now_iso8601()
    tr = ojp_tr_template.strip().replace("{{timestamp}}", now_iso8601)
    tr = tr.replace("{{origin_ref}}", str(a_bpuic)).replace("{{origin_name}}", a_name)
    tr = tr.replace("{{destin_ref}}", str(b_bpuic)).replace("{{destin_name}}", b_name)
    tr = tr.replace("{{arrdep}}", departure_time_iso8601)
    body_bytes = str(tr).encode('utf-8')
    response = session.post(url, data=body_bytes, headers=headers)
    status, size = response.status_code, len(response.content)
    if response.status_code != 200:
        if data_test:
            data_test.log_failure(f"ojp20 TR returned status code {status}.")
    if return_as.lower() == "bytes":
        return status, size, response.content
    response_str = response.content.decode('utf-8')
    if return_as.lower().endswith('xml'):
        try:
            return status, size, etree.XML(response.content)
        except Exception as e:
            return status, size, f"<xml><ERROR>Failed to render response {response_str[:30]}... as XML, exception: {str(e)}.</ERROR></xml>"
    if return_as.lower().endswith('dict'):
        try:
            return status, size, xml_to_dict(response.content)
        except Exception as e:
            return status, size, {"ERROR": f"Failed to render response {response_str[:30]}... as a dict.", "Exception": str(e)}

    return status, size, response_str


def ojp20_triprequest(a_bpuic: str, b_bpuic: str, departure_time_iso8601 = _now_iso8601(), return_as = "str", data_test: DataTest = None) -> tuple:
    """A simple access to the OJP 2.0 TripRquest, with A and B (bpuic), optional departure time.
    Depending on "return_as", returns a bytes response ("bytes"), a XML str ("str", default), or a lxml _Element object ("xml", "lxml") or dict ("dict").
    Returns the HTTPS status code, the size in bytes,  and the desired object/format."""
    a_name, b_name = _sp_name_for_bpuic(a_bpuic), _sp_name_for_bpuic(b_bpuic)
    url = "https://api.opentransportdata.swiss/ojp20"
    return ojp_trip_request(url, a_bpuic, a_name, b_bpuic, b_name, departure_time_iso8601, return_as, OJP_TR_TEMPLATE, data_test, headers)

def ojp10_triprequest(a_bpuic: str, a_name: str, b_bpuic: str, b_name: str, departure_time_iso8601 = _now_iso8601(), return_as = "str", data_test: DataTest = None) -> tuple:
    """A simple access to the OJP 1.0 TripRquest, with A and B (bpuic), optional departure time.
    Depending on "return_as", returns a bytes response ("bytes"), a XML str ("str", default), or a lxml _Element object ("xml", "lxml") or dict ("dict").
    Returns the HTTPS status code, the size in bytes,  and the desired object/format."""
    url1 = "https://api.opentransportdata.swiss/ojp2020"
    return ojp_trip_request(url1, a_bpuic, a_name, b_bpuic, b_name, departure_time_iso8601, return_as, OJP1_TR_TEMPLATE, data_test, headers_ojp10)


if __name__ == '__main__':
    print(f"{__file__} - simple tests")
    a, b = '8507000', '8503000'
    print(f"OJP 2.0 TR {get_service_point('number', a)['designationOfficial']} -> {get_service_point('number', b)['designationOfficial']} -- saving responses to files in ./data folder.")

    status, size, xml_bytes = ojp20_triprequest(a, b, return_as='bytes')
    print(f"Response with {status} status code, type={type(xml_bytes)}, {size} bytes.")
    open("data/ojp20_tr_raw.xml", mode='wb').write(xml_bytes)
    open("data/ojp20_tr_prettified.xml", encoding='utf-8-sig', mode='w').write(prettify_xml_bytes(xml_bytes))

    xml_dict = xml_to_dict(xml_bytes)
    open("data/ojp20_tr.json", encoding='utf-8-sig', mode='w').write(json.dumps(xml_dict, ensure_ascii=False, indent=2))

    print("Done.")

