"""
Tests mandatory fields and mandatory files in HRDF datasets.
"""

import io
import os
import re
import zipfile
import tempfile
from utilities.test_utilities import DataTest
from urllib.request import Request, urlopen
from urllib.parse import urljoin
from typing import List, Dict, Tuple, Optional

EXPECTED_FILES = [
    "attribut", "bahnhof", "betrieb", "bfkoord", "bhfart",
    "bitfeld", "bitfield", "eckdaten", "fplan", "infotext", "region", "zugart"
]

"""to do: add entry below for BITFIELD"""

HRDF_HEADERS = {
    "attribut": "*F 09 1",
    "bahnhof": "*F 01 1",
    "betrieb": "*F 28 1",
    "bfkoord": "*F 02 1",
    "bhfart": "*F 30 1",
    "bitfeld": "*F 05 1",
    "bitfield": "*F 05 1",
    "eckdaten": "*F 04 1",
    "fplan": "*F 03 1",
    "infotext": "*F 11 1",
    "region": "*F 45 1",
    "zugart": "*F 06 1"
}

HRDF_STOP_TYPES = ['SSI', 'SDI', 'SSS', 'SDS', 'SSD', 'SDD']

def is_zip_bytes(data: bytes) -> bool:
    return len(data) >= 4 and data[:2] == b'PK'

def try_decode_lines(data: bytes) -> List[str]:
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            text = data.decode(enc)
            return text.splitlines()
        except UnicodeDecodeError:
            continue
    text = data.decode("utf-8", errors="ignore")
    return text.splitlines()


def read_text_file(path: str) -> List[str]:
    with open(path, "rb") as f:
        data = f.read()
    return try_decode_lines(data)


def download_bytes_following_zip(url: str, data_test: DataTest, max_hops: int = 3) -> Tuple[int, Dict[str, str], bytes, str]:
    current_url = url
    seen = set()

    for hop in range(max_hops + 1):
        if current_url in seen:
            data_test.log_warning(f"Redirection loop suspected at {current_url}")
            break
        seen.add(current_url)

        req = Request(current_url, headers={"User-Agent": "hrdf-odv-tester/1.0"})
        with urlopen(req) as resp:
            status = getattr(resp, "status", 200)
            headers = {k.lower(): v for k, v in resp.getheaders()}
            final_url = resp.geturl()
            raw = resp.read()

        if is_zip_bytes(raw) or headers.get("content-type", "").startswith("application/zip") or \
                ("content-disposition" in headers and ".zip" in headers["content-disposition"].lower()):
            return status, headers, raw, final_url

        lines = try_decode_lines(raw)
        html = "\n".join(lines)
        zip_candidates = re.findall(r'href="([^"]+\.zip[^"]*)"', html, flags=re.IGNORECASE)
        resource_candidates = re.findall(r'href="([^"]*resource_permalink[^"]*)"', html, flags=re.IGNORECASE)
        candidates = zip_candidates + resource_candidates

        if not candidates:
            dl_candidates = re.findall(r'href="([^"]*/download/[^"]+)"', html, flags=re.IGNORECASE)
            candidates = dl_candidates

        if candidates:
            next_url = urljoin(final_url, candidates[0])
            data_test.log_info(f"Following link to potential ZIP: {next_url}")
            current_url = next_url
            continue

        return status, headers, raw, final_url

    data_test.log_warning(f"Max hops ({max_hops}) reached while trying to locate ZIP.")
    return 0, {}, b"", current_url


def unzip_bytes_to_temp(raw_zip: bytes) -> str:
    tmp_dir = tempfile.mkdtemp(prefix="hrdf_odv_")
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as zf:
        zf.extractall(tmp_dir)
    return tmp_dir


def find_all_paths(root_dir: str) -> List[str]:
    all_paths = []
    for r, _, files in os.walk(root_dir):
        for f in files:
            all_paths.append(os.path.join(r, f))
    return all_paths


def find_expected_file(root_dir: str, expected_name: str) -> Optional[str]:
    for r, _, files in os.walk(root_dir):
        for f in files:
            if f == expected_name:
                return os.path.join(r, f)
    return None


def validate_headers(file_map: Dict[str, str], data_test: DataTest) -> bool:
    ok = True
    for fname, header in HRDF_HEADERS.items():
        path = file_map.get(fname)
        if not path:
            ok = False
            data_test.log_failure(f"File '{fname}' missing – Header can't be checked.")
            continue
        lines = read_text_file(path)
        first_non_empty = None
        for ln in lines:
            if ln.strip():
                first_non_empty = ln.strip()
                break
        if not first_non_empty:
            ok = False
            data_test.log_failure(f"File '{fname}' empty – Header not found.")
            continue
        if first_non_empty != header:
            ok = False
            data_test.log_failure(f"Header of file '{fname}' not correct. Expected: '{header}', found: '{first_non_empty}'")
        else:
            data_test.log_info(f"Header of file '{fname}' is correct.")
    return ok


def check_attribut(path: str, data_test: DataTest):
    lines = read_text_file(path)
    data_test.test(
        condition=(len(lines) > 1),
        if_false_log_warning=f"'attribut' only has header or is empty."
    )

def check_betrieb(path: str, data_test: DataTest):
    lines = read_text_file(path)
    data_test.test(
        condition=(len(lines) > 1),
        if_false_log_warning="'betrieb' only has header or is empty."
    )


def check_bitfeld(path: str, data_test: DataTest):
    lines = read_text_file(path)
    payload = [ln for ln in lines if ln.strip() and not ln.startswith("*F")]
    pattern = re.compile(r'^\d{6,}\s+[0-9A-F]+$')
    any_match = any(pattern.match(ln.strip()) for ln in payload)
    data_test.test(
        condition=any_match,
        if_false_log_warning="'bitfeld' doesn't contain entries such as '<id> <HEX>'."
    )

def check_bitfield(path: str, data_test: DataTest):
    lines = read_text_file(path)
    payload = [ln for ln in lines if ln.strip() and not ln.startswith("*F")]
    pattern = re.compile(r'^\d{6,}\s+[0-9A-F]+$')
    any_match = any(pattern.match(ln.strip()) for ln in payload)
    data_test.test(
        condition=any_match,
        if_false_log_warning="'bitfield' doesn't contain entries such as '<id> <HEX>'."
    )


def check_eckdaten(path: str, data_test: DataTest):
    lines = read_text_file(path)
    payload = [ln for ln in lines if ln.strip() and not ln.startswith("*F")]
    has_start = any(re.search(r'\d{2}\.\d{2}\.\d{4}\s+Fahrplanstart', ln) for ln in payload)
    has_end = any(re.search(r'\d{2}\.\d{2}\.\d{4}\s+Fahrplanende', ln) for ln in payload)
    has_title = any(re.search(r'^"Angebotsplan\s+\d{4}"$', ln.strip()) for ln in payload)
    data_test.test(
        condition=has_start and has_end and has_title,
        if_false_log_failure="'eckdaten' missing timetable start / end or title."
    )


def check_fplan(path: str, data_test: DataTest):
    lines = read_text_file(path)
    payload = [ln for ln in lines if ln.strip() and not ln.startswith("*F")]
    has_trip = any(ln.strip().startswith("*T ") for ln in payload)
    has_g_tel = any(ln.strip().startswith("*G TEL") for ln in payload)
    has_a_ve = any(ln.strip().startswith("*A VE") for ln in payload)
    stop_line_re = re.compile(r'^\d+\s+(?:' + "|".join(HRDF_STOP_TYPES) + r')\b')
    has_stop_line = any(stop_line_re.match(ln.strip()) for ln in payload)
    data_test.test(
        condition=has_trip,
        if_false_log_failure="'fplan' doesn't contain '*T' trip."
    )
    data_test.test(
        condition=has_g_tel,
        if_false_log_warning="'fplan' doesn't contain '*G TEL'."
    )
    data_test.test(
        condition=has_a_ve,
        if_false_log_warning="'fplan' doesn't contain '*A VE'."
    )
    data_test.test(
        condition=has_stop_line,
        if_false_log_warning="'fplan' doesn't contain Pseudo-Stop-Rows."
    )
    has_percent = any('%' in ln for ln in payload)
    data_test.test(
        condition=has_percent,
        if_false_log_warning="'fplan' doesn't contain '%'."
    )


def check_infotext(path: str, data_test: DataTest):
    lines = read_text_file(path)
    payload = [ln for ln in lines if ln.strip() and not ln.startswith("*F") and not ln.startswith("% ")]
    has_id_line = any(re.match(r'^\d{6,}\s+.+', ln.strip()) for ln in payload)
    data_test.test(
        condition=has_id_line,
        if_false_log_warning="'infotext' doesn't contain '<id> <text>'."
    )


def check_region(path: str, data_test: DataTest):
    lines = read_text_file(path)
    payload = [ln for ln in lines if ln.strip()]
    has_r = any(ln.strip().startswith("*R ") for ln in payload)
    has_as_ac = any(ln.strip() in ("*AS", "*AC") or ln.strip().startswith("*AS") or ln.strip().startswith("*AC") for ln in payload)
    data_test.test(
        condition=has_r,
        if_false_log_failure="'region' doesn't contain '*R' regions."
    )
    data_test.test(
        condition=has_as_ac,
        if_false_log_warning="'region' doesn't contain '*AS' or '*AC'."
    )


def check_zugart(path: str, data_test: DataTest):
    lines = read_text_file(path)
    text = "\n".join(lines)
    has_tel_10 = "TEL 10" in text and "DRT" in text
    data_test.test(
        condition=has_tel_10,
        if_false_log_warning="'zugart' doesn't contain 'TEL 10 ... DRT'."
    )


def check_bahnhof(path: str, data_test: DataTest):
    lines = read_text_file(path)
    payload = [ln for ln in lines if ln.strip() and not ln.startswith("*F")]
    has_id_and_name = any(re.match(r'^\d+\s{2,}.+', ln) for ln in payload)
    data_test.test(
        condition=has_id_and_name,
        if_false_log_warning="'bahnhof' doesn't contain '<id>  <name>'."
    )


def check_bfkoord(path: str, data_test: DataTest):
    lines = read_text_file(path)
    payload = [ln for ln in lines if ln.strip() and not ln.startswith("*F")]
    has_coord = any(re.match(r'^\S+\s+\d+\.\d+\s+\d+\.\d+', ln.strip()) for ln in payload)
    data_test.test(
        condition=has_coord,
        if_false_log_warning="'bfkoord' doesn't contain '<id> <lon> <lat>'."
    )


def check_bhfart(path: str, data_test: DataTest):
    lines = read_text_file(path)
    payload = [ln for ln in lines if ln.strip() and not ln.startswith("*F")]
    has_p = any(re.search(r'\bP\b', ln) for ln in payload)
    has_e = any(re.search(r'\bE\b', ln) for ln in payload)
    data_test.test(
        condition=has_p,
        if_false_log_warning="'bhfart' doesn't contain 'P'."
    )
    data_test.test(
        condition=has_e,
        if_false_log_warning="'bhfart' doesn't contain 'E'."
    )


def check_all_contents(file_map: Dict[str, str], data_test: DataTest):
    check_attribut(file_map["attribut"], data_test)
    check_betrieb(file_map["betrieb"], data_test)
    check_bitfeld(file_map["bitfeld"], data_test)
    """check_bitfield(file_map["bitfield"], data_test)"""
    check_eckdaten(file_map["eckdaten"], data_test)
    check_fplan(file_map["fplan"], data_test)
    check_infotext(file_map["infotext"], data_test)
    check_region(file_map["region"], data_test)
    check_zugart(file_map["zugart"], data_test)
    check_bahnhof(file_map["bahnhof"], data_test)
    check_bfkoord(file_map["bfkoord"], data_test)
    check_bhfart(file_map["bhfart"], data_test)


def check_hrdf(url, data_test = None) -> DataTest:
    if data_test is None:
        data_test = DataTest(name="check_hrdf")

    try:
        status, headers, raw, final_url = download_bytes_following_zip(url, data_test)
        is_status_ok = data_test.test(
            condition=(status and status < 400 and raw),
            if_false_log_failure=f"Download error or empty. Status={status}, final_url={final_url}"
        )
        if not is_status_ok:
            return data_test

        if not is_zip_bytes(raw):
            data_test.log_failure("Didn't find a ZIP file. Aborting.")
            return data_test

        tmp_dir = unzip_bytes_to_temp(raw)

        file_map: Dict[str, str] = {}
        for name in EXPECTED_FILES:
            p = find_expected_file(tmp_dir, name)
            if p:
                file_map[name] = p

        missing = [n for n in EXPECTED_FILES if n not in file_map]
        data_test.test(
            condition=(len(missing) == 0),
            if_false_log_failure=f"Missing files: {', '.join(missing)}"
        )

        check_all_contents(file_map, data_test)
        return data_test

    except Exception as e:
        data_test.log_exception("Unforeseen exception during test run.", e)
        return data_test