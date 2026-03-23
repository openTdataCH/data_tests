"""
Test the bruno files to check the APIs

The test does these checks:
- load a resource Bruno Resource
- execute the Bruno API Request
- check the output from Bruno (assertions, per-request status, totals)

The run method requires no config at all (hence, no 'config' parameter).
"""
import json
import os
import re

from utilities.test_utilities import DataTest
from tests.bruno_tests.bruno_utilities import BrunoRunner
from utilities.file_and_path_utilities import get_path

RESOURCES = {
    "OJP2.0": get_path("tests/bruno_tests/data/collection/OJP_2.0_2026_01"),
    "OJP1.0": get_path("tests/bruno_tests/data/collection/OJP_1.0_2026_01"),
    "OJP1.0_Sample": get_path("tests/bruno_tests/data/collection/sample_test"),
    "OJP2.0_Sample": get_path("tests/bruno_tests/data/collection/sample_test_20")
}

_HEADER_RE = re.compile(r"(.+?)\s+\((\d+)\s+OK\)\s+-\s+(\d+)\s+ms")

def load_bruno_env(file_path: str, env_name: str) -> dict:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        environments = data.get("environments", [])

        target_env = None
        for env in environments:
            if env.get("name") == env_name:
                target_env = env
                break

        if target_env is None:
            available_names = [e.get("name") for e in environments]
            return {}

        extracted_vars = {}
        variables = target_env.get("variables", [])

        for var in variables:
            name = var.get("name")
            value = var.get("value")

            if var.get("enabled", True) and name:
                extracted_vars[name] = str(value) if value is not None else ""

        return extracted_vars
    except Exception as e:
        print(f"Critical error when loading .env file: {e}")
        return {}

def get_all_bru_files(directory: str) -> list:
    """searches recursively in a filestructure for .bru files."""
    bru_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            lower = file.lower()
            if not lower.endswith(".bru"):
                continue
            if lower.endswith("folder.bru") or lower.endswith("collection.bru"):
                continue
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
            data_test.log_failure(f"Version '{variant}' not found in RESOURCES.")
            return data_test
    else:
        selected_resources = RESOURCES

    total_requests = 0
    total_failures = 0
    total_conditions = 0
    total_conditions_failed = 0

    for env_name, base_directory in selected_resources.items():
        data_test.log_info(f"--- Start Tests: {env_name} ---")

        env = load_bruno_env(env_file, env_name)
        if not env:
            data_test.log_failure(f"Abort: No variables found for {env_name}.")
            continue

        test_files = get_all_bru_files(base_directory)
        if not test_files:
            data_test.log_warning(f"No test files found in {base_directory}.")
            continue

        data_test.log_info(f"Found {len(test_files)} files in {env_name}.")
        expected_amount = len(test_files)
        executed_tests = 0

        for file_path in test_files:
            if "node_modules" in file_path:
                continue

            abs_file_path = os.path.abspath(file_path)
            file_dir = os.path.dirname(abs_file_path)
            file_name = os.path.basename(abs_file_path)

            try:
                runner = BrunoRunner(file_name, data_test=data_test, working_dir=file_dir)
                report, executed, stdout = runner.run(env_vars=env, timeout=120, strict=False)

                match = _HEADER_RE.search(stdout) if stdout else None
                h_name = match.group(1) if match else file_name
                h_status = match.group(2) if match else "200"
                h_duration = match.group(3) if match else "0"

                if report and report.get("requests"):
                    req = report["requests"][0]
                    f_count = report["summary"]["assertions"]["failed"]
                    p_count = report["summary"]["assertions"]["passed"]

                    if f_count > 0:
                        data_test.log_failure(f"[FAILED] {h_name} (HTTP {h_status}, {h_duration}ms) | {p_count} Tests passed, {f_count} Tests failed")
                        for asrt in req["assertions"]:
                            if asrt["status"] == "failed":
                                data_test.log_warning(f"  ✕ {asrt['name']}: {asrt['message']}")
                                total_conditions_failed += 1
                        total_failures += 1
                    else:
                        data_test.log_info(f"[OK] {h_name} (HTTP {h_status}, {h_duration}ms) | {p_count} Tests passed")

                    total_conditions += p_count + f_count
                    executed_tests += p_count

            except Exception as e:
                data_test.log_failure(f"Critical error in {file_name}: {str(e)}")
                total_failures += 1
            total_requests += 1

        if total_requests < expected_amount:
            data_test.log_failure(f"Test count low: {executed_tests} (Expected min: {expected_amount})")

    data_test.log_info(f"Finished execution. Calls: {total_requests} | Failures: {total_failures}. | "
                       f"Total conditions: {total_conditions} | Failed conditions: {total_failures}.")
    return data_test

if __name__ == '__main__':
    tr = run(variant="OJP2.0_Sample")
    print(tr)