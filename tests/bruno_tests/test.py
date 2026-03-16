"""Test the bruno files to check the APIs

The test does these checks:
- load a resource Bruno Resource
- execute the Bruno API Request
TODO: checks of the output from Bruno.

The run method requires no config at all (hence, no 'config' parameter).
"""
import json

from utilities.test_utilities import DataTest
from tests.bruno_tests.bruno_utilities import BrunoRunner
import os
from utilities.file_and_path_utilities import get_path

RESOURCES = {
    "OJP2.0": get_path("tests/bruno_tests/data/collection/OJP_2.0_2026_01"),
    "OJP1.0": get_path("tests/bruno_tests/data/collection/OJP_1.0_2026_01"),
    "OJP1.0_Sample": get_path("tests/bruno_tests/data/collection/sample_test"),
    "OJP2.0_Sample": get_path("tests/bruno_tests/data/collection/sample_test_20")
}

def load_bruno_env(file_path: str, env_name: str) -> dict:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
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
        print(f"Kritischer Fehler beim Laden der Env-Datei: {e}")
        return {}

def get_all_bru_files(directory: str) -> list:
    """searches recursively in a filestructure for .bru files."""
    bru_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".bru"):
                if file.lower().endswith("folder.bru"):
                    continue
                if file.lower().endswith("collection.bru"):
                    continue
                full_path = os.path.join(root, file)
                bru_files.append(full_path)

    bru_files.sort()
    return bru_files

def run(variant: str = None) -> DataTest:
    data_test = DataTest(name=f"bruno_test_{variant}" if variant else "bruno_test_all")

    env_file = get_path("tests/bruno_tests/data/variables/bruno-global-environments.json")

    if variant:
        if variant in RESOURCES:
            selected_resources = {variant: RESOURCES[variant]}
        else:
            data_test.log_failure(f"Fehler: Version '{variant}' nicht in RESOURCES gefunden.")
            return data_test
    else:
        selected_resources = RESOURCES

    test_amount = 0

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

        for file_path in test_files:
            if "node_modules" in file_path:
                continue
            try:
                runner = BrunoRunner(file_path, data_test=data_test)
                data, size, _ = runner.run(env_vars=env)
                test_amount += 1

                if not data:
                    data_test.log_failure(f"[FAILED] {file_path}")
            except Exception as e:
                data_test.log_failure(f"Critical error executing {file_path}: {str(e)}")

        if test_amount < expected_amount:
            data_test.log_failure(f"Test count low: {test_amount} (Expected min: {expected_amount})")

    data_test.log_info(f"Finishing execution. Total tests: {test_amount}")
    return data_test

if __name__ == '__main__':
    tr = run(variant="OJP2.0_Sample")
    print(tr)