"""
Tests mandatory fields for HRDF Converter in Netex datasets.
"""

import io
import re
import zipfile
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Tuple
from utilities.test_utilities import DataTest

def parse_namespaces(root) -> dict:
    m = re.match(r"^\{([^\}]+)\}", root.tag)
    netex_ns = m.group(1) if m else "http://www.netex.org.uk/netex"
    return {
        "n": netex_ns,
        "gml": "http://www.opengis.net/gml/3.2",
        "siri": "http://www.siri.org.uk/siri"
    }

def is_hhmmss(s: str) -> bool:
    return bool(re.fullmatch(r"\d{2}:\d{2}:\d{2}", s or ""))

def is_binary_str(s: str) -> bool:
    return bool(re.fullmatch(r"[01]+", s or ""))

def text_or_none(elem):
    return elem.text if elem is not None else None

def is_point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    if not polygon: return False
    x, y = point
    inside = False
    n = len(polygon)
    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
            if p1y != p2y:
                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
            else:
                xinters = p1x
            if p1x == p2x or x <= xinters:
                inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def check_netex(url, data_test):
    if data_test is None:
        data_test = DataTest(name="check_netex")

    data_test.log_info(f"Checking Netex file from {url}")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SBB-DataTest/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
    except Exception as e:
        data_test.log_exception("Download failed.", e)
        return data_test

    zf = zipfile.ZipFile(io.BytesIO(content))
    xml_name = [n for n in zf.namelist() if n.lower().endswith(".xml")][0]
    with zf.open(xml_name, "r") as f:
        root = ET.fromstring(f.read())

    ns = parse_namespaces(root)

    # Validity
    valid_between = root.find(".//n:CompositeFrame//n:ValidBetween", ns)
    if valid_between is not None:
        from_date = text_or_none(valid_between.find("n:FromDate", ns))
        to_date = text_or_none(valid_between.find("n:ToDate", ns))
        data_test.test(condition=bool(from_date and to_date), if_false_log_failure="ValidBetween dates missing.")

    # Availability Conditions
    acs = root.findall(".//n:AvailabilityCondition", ns)
    for ac in acs:
        ac_id = ac.get("id")
        vdb = text_or_none(ac.find(".//n:ValidDayBits", ns))
        if not data_test.test(condition=bool(vdb and "1" in vdb),
                              if_false_log_warning=f"AC {ac_id} has invalid/empty DayBits."):
            continue

    # Service Journey Patterns
    patterns_map = {p.get("id"): p for p in root.findall(".//n:ServiceJourneyPattern", ns)}
    sjs = root.findall(".//n:ServiceJourney", ns)

    corrupt_patterns = []
    for sj in sjs:
        sj_id = sj.get("id")
        sjpr = sj.find("n:ServiceJourneyPatternRef", ns)
        p_ref = sjpr.get("ref") if sjpr is not None else None

        if p_ref in patterns_map:
            p_elem = patterns_map[p_ref]
            points = p_elem.findall(".//n:StopPointInJourneyPattern", ns)
            links = p_elem.findall(".//n:ServiceLinkInJourneyPattern", ns)
            if len(points) < 2 or len(links) < 1:
                corrupt_patterns.append(f"{p_ref} (in SJ {sj_id})")

    data_test.test(
        condition=(len(corrupt_patterns) == 0),
        if_false_log_failure=f"Found {len(corrupt_patterns)} ServiceJourneyPatternRef with empty StopPointInJourneyPattern/ServiceLinkInJourneyPattern (e.g. {corrupt_patterns[:2]})."
    )

    # Operator and PrivateCodes
    operators = root.findall(".//n:Operator", ns)
    for op in operators:
        op_id = op.get("id")
        pc = text_or_none(op.find(".//n:PrivateCode", ns))
        data_test.test(condition=bool(pc), if_false_log_failure=f"Operator {op_id} missing PrivateCode.")

    # Flexible Areas and Geofencing
    areas_polygons = {}
    for fa in root.findall(".//n:FlexibleArea", ns):
        fa_id = fa.get("id")
        pos_elems = fa.findall(".//gml:pos", ns)
        poly_points = []
        for pos in pos_elems:
            try:
                coords = pos.text.strip().split()
                poly_points.append((float(coords[0]), float(coords[1])))
            except: continue
        if len(poly_points) >= 3:
            areas_polygons[fa_id] = poly_points

    # extract stops
    stop_places = root.findall(".//n:StopPlace", ns)
    valid_stops = []
    for sp in stop_places:
        lon = text_or_none(sp.find(".//n:Longitude", ns))
        lat = text_or_none(sp.find(".//n:Latitude", ns))
        if lon and lat:
            valid_stops.append((float(lon), float(lat)))

    # check if areas contain at least one stop
    for area_id, poly in areas_polygons.items():
        contained = any(is_point_in_polygon(pt, poly) for pt in valid_stops)
        data_test.test(
            condition=contained,
            if_false_log_warning=f"FlexibleArea {area_id} contains no StopPlaces."
        )

    return data_test