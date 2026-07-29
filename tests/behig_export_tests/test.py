"""
Tests the behig_export files.
The run method requires no config at all (hence, no 'config' parameter).
1. The test connects via SFTP to the SBB FTP Server and checks if the file is newer than a threshold.
2. The test downloads the csv file and checks the columns according to the date.
3. The test validates the content of the  file against a dynamic Schema.
4. The test documents and returns data_test objects.
"""
import os
import re
import json
import io
from datetime import datetime, timezone
import paramiko

from utilities.csv_utilities import load_csv_streaming_and_do_data_checks
from utilities.file_and_path_utilities import get_path
from utilities.json_utilities import load_json_file
from utilities.test_utilities import DataTest

TEST_NAME = "behig_export_tests"
CONFIG_FILE = f"tests/{TEST_NAME}/data/config.json"
config = load_json_file(CONFIG_FILE)
if not config:
    raise FileNotFoundError(f"Config file not found at {CONFIG_FILE}")

SFTP_HOST = config.get("sftp_host")
SFTP_PORT = config.get("sftp_port")
SFTP_USER = config.get("sftp_user")
SFTP_PASSWORD = config.get("sftp_password")
REMOTE_FILE_PATH = config.get("remote_file_path")
AGE_IN_DAYS_THRESHOLD = config.get("age_in_days_threshold")


def prepare_schema(file_stream: io.TextIOBase, file_schema: dict, delimiter: str = ";") -> dict:
    file_stream.seek(0)
    header_line = file_stream.readline().strip()
    headers = [h.strip().strip('"') for h in header_line.split(delimiter)]
    file_stream.seek(0)
    updated_schema = json.loads(json.dumps(file_schema))

    if "columns" not in updated_schema:
        updated_schema["columns"] = {}

    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # e.g. 2026-07-23

    for col in headers:
        if date_pattern.match(col) and col not in updated_schema["columns"]:
            updated_schema["columns"][col] = {
                "required": False,
                "regex": "^[01]$"
            }

    return updated_schema


def run():
    data_test = DataTest(name=TEST_NAME)

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    sftp = None

    try:
        ssh_client.connect(SFTP_HOST, port=SFTP_PORT, username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = ssh_client.open_sftp()

        remote_stat = sftp.stat(REMOTE_FILE_PATH)
        file_mtime = datetime.fromtimestamp(remote_stat.st_mtime, tz=timezone.utc)

        age_in_days = (datetime.now(timezone.utc) - file_mtime).total_seconds() / 86400.0

        data_test.test(
            age_in_days < AGE_IN_DAYS_THRESHOLD,
            if_false_log_failure=f"FAILED age check: File is {age_in_days:.2f} days old (threshold: {AGE_IN_DAYS_THRESHOLD})."
        )

        with sftp.open(REMOTE_FILE_PATH, "rb") as remote_file:
            in_memory_file = io.BytesIO(remote_file.read())

        text_stream = io.TextIOWrapper(in_memory_file, encoding="utf-8")

        schema_path = get_path(f"tests/{TEST_NAME}/data/behig_schema_config.json")
        if os.path.exists(schema_path):
            master_config = load_json_file(schema_path)
            if master_config:
                csv_schema_spec = master_config.get("csv_schema_spec", {})
                file_schema = csv_schema_spec.get("zugnummer_behig.csv", {})

                if file_schema:
                    dynamic_schema = prepare_schema(text_stream, file_schema, delimiter=";")

                    data_test = load_csv_streaming_and_do_data_checks(
                        stream=text_stream,
                        schema_config=dynamic_schema,
                        delimiter=";",
                        filename="zugnummer_behig.csv",
                        data_test=data_test
                    )
                else:
                    data_test.log_failure(f"No configuration for 'zugnummer_behig.csv' in {schema_path} found.")
            else:
                data_test.log_warning(f"Schema config file {schema_path} is empty or invalid.")
        else:
            data_test.log_warning(f"Schema config file {schema_path} does not exist.")

    except Exception as e:
        data_test.log_exception(f"Error during SFTP operation: {str(e)}", e)
    finally:
        if sftp:
            sftp.close()
        ssh_client.close()

    data_test.log_info(f"Test completed for file: {REMOTE_FILE_PATH}")
    return data_test


if __name__ == '__main__':
    tr = run()
    print(tr)