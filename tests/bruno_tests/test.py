"""
Test the Bruno files to check the APIs.

Checks:
- Load Bruno Resource configuration
- Execute the Bruno API Request
- Validate output (assertions, HTTP status, execution times)
"""
import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from utilities.test_utilities import DataTest
from tests.bruno_tests.bruno_utilities import BrunoRunner
from utilities.file_and_path_utilities import get_path

_HEADER_RE = re.compile(r"(.+?)\s+\((\d+)\s+[^)]+\)\s+-\s+(\d+)\s+ms")


def _find_collection_file(start_directory: str) -> Optional[str]:
    """Find nearest collection.bru by walking up from the resource directory."""
    current = os.path.abspath(start_directory)
    while True:
        candidate = os.path.join(current, "collection.bru")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _load_collection_vars(collection_file: Optional[str]) -> Dict[str, str]:
    """Parse `vars:pre-request` block from collection.bru into a dict."""
    if not collection_file:
        return {}

    vars_dict = {}
    in_vars_block = False

    try:
        with open(collection_file, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if line.startswith("vars:pre-request") and line.endswith("{"):
                    in_vars_block = True
                    continue

                if in_vars_block and line == "}":
                    break

                if not in_vars_block or not line or line.startswith("//"):
                    continue

                match = re.match(r"^([A-Za-z0-9_-]+):\s*(.+)$", line)
                if match:
                    key = match.group(1)
                    val = match.group(2).strip().strip("\"'")
                    vars_dict[key] = val
    except IOError as e:
        print(f"[Warning] Could not read collection file {collection_file}: {e}")

    return vars_dict


def _enrich_env_with_collection_vars(base_directory: str, env: dict) -> dict:
    collection_file = _find_collection_file(base_directory)
    collection_vars = _load_collection_vars(collection_file)

    merged_env = dict(env)
    merged_env.update(collection_vars)

    if "isoTimestamp" not in merged_env:
        merged_env["isoTimestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return merged_env


def load_resources() -> dict:
    json_path = get_path("tests/bruno_tests/data/variables/resources.json")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw_resources = json.load(f)

        return {
            key: {
                "path": get_path(data["path"]),
                "env_name": data["env_name"]
            }
            for key, data in raw_resources.items()
        }
    except (IOError, json.JSONDecodeError) as e:
        print(f"[Error] Failed to load resources.json: {e}")
        return {}

RESOURCES = load_resources()

def load_bruno_env(file_path: str, env_name: str) -> dict:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        environments = data.get("environments", [])
        target_env = next((e for e in environments if e.get("name") == env_name), None)

        if target_env is None:
            return {}

        extracted_vars = {}
        for var in target_env.get("variables", []):
            name = var.get("name")
            value = var.get("value")
            if var.get("enabled", True) and name:
                extracted_vars[name] = str(value) if value is not None else ""

        return extracted_vars
    except (IOError, json.JSONDecodeError) as e:
        print(f"[Error] Critical error loading Bruno env file '{file_path}': {e}")
        return {}

def get_all_bru_files(directory: str) -> List[str]:
    """Searches recursively in a directory for executable .bru files."""
    bru_files = []
    for root, _, files in os.walk(directory):
        if "node_modules" in root:
            continue

        for file in files:
            lower = file.lower()
            if lower.endswith(".bru") and not (lower.endswith("folder.bru") or lower.endswith("collection.bru")):
                bru_files.append(os.path.join(root, file))

    bru_files.sort()
    return bru_files

def run(variant: str = None) -> DataTest:
    data_test = DataTest(name=f"bruno_test_{variant}" if variant else "bruno_test_all")
    env_file = get_path("tests/bruno_tests/data/variables/bruno-global-environments.json")

    if variant:
        if variant in RESOURCES:
            selected_resources = {variant: RESOURCES[variant]}
        else:
            selected_resources = {k: v for k, v in RESOURCES.items() if v["env_name"] == variant}
            if not selected_resources:
                data_test.log_failure(f"Version or Env '{variant}' not found in RESOURCES.")
                return data_test
    else:
        selected_resources = RESOURCES

    total_requests = 0
    total_failures = 0
    total_conditions = 0
    total_conditions_failed = 0

    for resource_key, resource_data in selected_resources.items():
        base_directory = resource_data["path"]
        env_name = resource_data["env_name"]

        data_test.log_info(f"--- Start Tests: {env_name} ---")

        env = load_bruno_env(env_file, env_name)
        if not env:
            data_test.log_failure(f"Abort: No variables found for {env_name}.")
            continue

        env = _enrich_env_with_collection_vars(base_directory, env)
        test_files = get_all_bru_files(base_directory)
        if not test_files:
            data_test.log_warning(f"No test files found in {base_directory}.")
            continue

        data_test.log_info(f"Found {len(test_files)} files in {env_name}.")
        executed_in_resource = 0
        abs_base_dir = os.path.abspath(base_directory)

        for file_path in test_files:
            abs_file_path = os.path.abspath(file_path)
            relative_file_path = os.path.relpath(abs_file_path, abs_base_dir)
            file_name = os.path.basename(abs_file_path)

            try:
                runner = BrunoRunner(relative_file_path, data_test=data_test, working_dir=abs_base_dir)
                report, executed, stdout = runner.run(env_vars=env, timeout=120, strict=False)

                if not report or "requests" not in report or not report["requests"]:
                    data_test.log_warning(f"--- DEBUG for {file_name} ---")
                    data_test.log_warning(f"STDOUT: {stdout}")
                    data_test.log_warning(f"REPORT: {json.dumps(report, indent=2) if report else 'None'}")

                match = _HEADER_RE.search(stdout) if stdout else None
                h_name = match.group(1) if match else file_name
                h_status = match.group(2) if match else "200"
                h_duration = match.group(3) if match else "0"

                if report and isinstance(report.get("requests"), list) and report["requests"]:
                    req = report["requests"][0]
                    req_assertions = req.get("assertions", [])

                    if req_assertions:
                        f_count = sum(1 for a in req_assertions if a.get("status") == "failed")
                        p_count = sum(1 for a in req_assertions if a.get("status") == "passed")
                    else:
                        summary_assertions = report.get("summary", {}).get("assertions", {})
                        f_count = summary_assertions.get("failed", 0)
                        p_count = summary_assertions.get("passed", 0)

                    if f_count > 0:
                        data_test.log_warning(f"[WARNING] {h_name} (HTTP {h_status}, {h_duration}ms) | {p_count} Tests passed, {f_count} Tests failed")
                        for asrt in req_assertions:
                            if asrt.get("status") == "failed":
                                asrt_name = asrt.get("name", "Unnamed assertion")
                                asrt_msg = asrt.get("message", "No message")
                                data_test.log_warning(f"  ✕ {asrt_name}: {asrt_msg}")
                                total_conditions_failed += 1
                        total_failures += 1
                    else:
                        data_test.log_info(f"[OK] {h_name} (HTTP {h_status}, {h_duration}ms) | {p_count} Tests passed")

                    total_conditions += (p_count + f_count)
                else:
                    data_test.log_warning(f"No valid report or requests found for {file_name}. STDOUT: {stdout}")
                    total_conditions_failed += 1

            except Exception as e:
                data_test.log_failure(f"Critical error in {file_name}: {str(e)}")
                total_failures += 1
            total_requests += 1
            executed_in_resource += 1

        if executed_in_resource < len(test_files):
            data_test.log_failure(f"Test count low in {env_name}: Ran {executed_in_resource} / Expected {len(test_files)}")

    data_test.log_info(f"Finished execution. Calls: {total_requests} | Failures: {total_failures}. | "
                       f"Total conditions: {total_conditions} | Failed conditions: {total_conditions_failed}.")
    return data_test

if __name__ == '__main__':
    tr = run(variant="OJP1.0_OnDemand")
    print(tr)