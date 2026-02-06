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

THRESHOLD_HOURS = 32


def check_jsonl_file(file_path):
    with open(file_path, 'r') as f:
        for line in f:
            json_data = json.loads(line)
            if 'logs' in json_data:
                logs_timestamp = datetime.fromisoformat(json_data['logs'][0:19])
                if logs_timestamp > datetime.now() - timedelta(hours=THRESHOLD_HOURS):
                    n_exceptions = json_data.get('n_exceptions', 0)
                    n_failures = json_data.get('n_failures', 0)
                    if n_exceptions > 0 or n_failures > 0:
                        return True, json_data['logs']
    return False, None


def process_files():
    all_reports = []
    test_reports_folder = CONFIG['folders']['test_reports']
    for filename in os.listdir(test_reports_folder):
        if filename.endswith('.jsonl'):
            file_path = os.path.join(test_reports_folder, filename)
            valid, logs = check_jsonl_file(file_path)
            if valid:
                all_reports.append((filename, logs))

    if True:  # all_reports:
        subject = "DataTests: Daily Errors Report"
        body = Template("daily_report_mail_body.html")
        body.replace("hours", THRESHOLD_HOURS)
        body.replace("subject", subject)
        payload = "\n\n".join([f"\n{'='*100}\n{file_name}:\n{logs}" for file_name, logs in all_reports])
        body.replace("payload", payload)

        send_mail(subject=subject, recipients_comma_separated=get_prop("skiplus_support"), body=str(body))


if __name__ == "__main__":
    process_files()
