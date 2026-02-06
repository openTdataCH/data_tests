"""A script which goes through all JSONL (JsonLines) files in the given folder TEST_REPORTS_FOLDER,
loads each JSON line, and checks if it has:
 - at key "logs" a timestamp newer than X hours, and
 - at keys "n_exceptions" or "n_failures" a value greater than zero.
If so, add the file name as title, then the logs to a mail.
Finally, send a mail with the given body.
"""

import json
import os
from datetime import datetime, timedelta

from configuration import get_prop, CONFIG
from utilities.mail_utilities import send_mail
from utilities.template_utilities import Template

import logging

from utilities.test_utilities import html_report_from_json

THRESHOLD_HOURS = 32

LOG_FILE = os.path.join(CONFIG['folders']['logs'], "daily_report_mail.log")
logging.basicConfig(handlers=[logging.FileHandler(LOG_FILE, 'a', 'utf-8')], level=logging.INFO, format='%(asctime)s: %(levelname)s: %(message)s')


def load_affected_test_reports(file_path):
    """Load all test reports at the given path, for the given time range and having exceptions, failures or warnings."""
    affected_test_reports = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip().startswith("{"):
                json_data = json.loads(line.strip())
                if 'logs' in json_data:
                    logs_timestamp = datetime.fromisoformat(json_data['logs'][0:19])
                    if logs_timestamp > datetime.now() - timedelta(hours=THRESHOLD_HOURS):
                        n_exceptions = json_data.get('n_exceptions', 0)
                        n_failures = json_data.get('n_failures', 0)
                        n_warnings = json_data.get('n_warnings', 0)
                        if n_exceptions > 0 or n_failures > 0 or n_warnings > 0:
                            affected_test_reports.append(json_data)
    return affected_test_reports


def process_reports(body: Template):
    test_reports_folder = CONFIG['folders']['test_reports']
    for filename in [f[:-6] for f in os.listdir(test_reports_folder) if f.endswith('.jsonl')]:
        file_path = os.path.join(test_reports_folder, filename + ".jsonl")
        affected_test_reports = load_affected_test_reports(file_path)
        if len(affected_test_reports) > 0:
            body.append("payload", f"<h2>{filename}</h2>\n")
            for report in affected_test_reports:
                body.append("payload", html_report_from_json(report))


def process():
    logging.info("daily_report_mail.py started.")
    subject = "data_tests: Daily Report of Exceptions, Failures and Warnings"
    body = Template("daily_report_mail_body.html")
    body.replace("THRESHOLD_HOURS", THRESHOLD_HOURS)
    body.replace("subject", subject)

    process_reports(body)

    return_code, message = send_mail(subject=subject, recipients_comma_separated=get_prop("skiplus_support"), body=str(body))
    logging.info(f"daily_report_mail.py finished: {return_code}, {message}.")


if __name__ == "__main__":
    process()
