"""
Tests mandatory fields and mandatory files in GTFS datasets.
"""

import requests
import zipfile
import io
import json

from utilities.csv_utilities import load_csv_streaming_and_do_data_checks
from utilities.file_and_path_utilities import get_path
from utilities.test_utilities import DataTest

def check_gtfs(url: str, data_test=None):
    if data_test is None:
        data_test = DataTest(name="check_gtfs")
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        schema_path = get_path("utilities/gtfs_utilities/gtfs_schema_config.json")
        with open(schema_path, "r", encoding="utf-8") as schema_file:
            master_config = json.load(schema_file)

        gtfs_files_config = master_config.get("gtfs_files", {})

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            files_in_zip = z.namelist()

            # Run through all defined files in the schema config and check if they are present and valid
            for filename, file_schema in gtfs_files_config.items():
                is_required = file_schema.get("required_file", False)

                if filename not in files_in_zip:
                    if is_required:
                        data_test.log_failure(f"Mandatory file {filename} is missing in ZIP archive!")
                    continue

                if filename.endswith(".geojson"):
                    with z.open(filename) as f:
                        try:
                            geojson_data = json.loads(f.read().decode('utf-8'))
                            expected_keys = list(file_schema.get("columns", {}).keys())

                            missing_keys = [k for k in expected_keys if k not in geojson_data]
                            if missing_keys:
                                data_test.log_failure(f"Missing Keys in GeoJSON {filename}: {missing_keys}")

                        except json.JSONDecodeError as e:
                            data_test.log_failure(f"Error parsing JSON in {filename}: {e}")
                        except Exception as e:
                            data_test.log_failure(f"General error with GeoJSON {filename}: {e}")
                    continue

                with z.open(filename) as f:
                    text_stream = io.TextIOWrapper(f, encoding='utf-8-sig')

                    load_csv_streaming_and_do_data_checks(
                        stream=text_stream,
                        schema_config=file_schema,
                        delimiter=',',
                        data_test=data_test,
                        filename=filename
                    )

    except requests.exceptions.RequestException as e:
        data_test.log_failure(f"Download-Error (HTTP Request Error): {e}")
    except zipfile.BadZipFile:
        data_test.log_failure("The downloaded file is not a valid ZIP archive.")
    except Exception as e:
        data_test.log_failure(f"Unexpected error during GTFS check: {e}")

    return data_test