"""A script which generates an HTML file with the "history" of yesterday.
- goes through all JSONL (JsonLines) files in the given folder TEST_REPORTS_FOLDER,
- loads each JSON line, and checks if it has:
 - at key "logs" a timestamp of yesterday
 - at keys "n_exceptions" or "n_failures" a value greater than zero.
- if so, add the data to the history
- finally, store the HTML page as a file in folder ../data/html/history.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader

from configuration import CONFIG
from utilities.test_utilities import html_report_from_json


LOG_FILE = os.path.join(CONFIG['folders']['logs'], "daily_history.log")
logging.basicConfig(handlers=[logging.FileHandler(LOG_FILE, 'a', 'utf-8')], level=logging.INFO, format='%(asctime)s: %(levelname)s: %(message)s')
YESTERDAY = (datetime.now() - timedelta(days=0)).isoformat()[:10]
OUT_DIR = "data/html/history"
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = f"{OUT_DIR}/{YESTERDAY}.html"


def load_affected_test_reports(file_path):
    """Load all test reports at the given path, for the yesterday, and having exceptions, failures or warnings."""
    affected_test_reports = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith("{"):
                json_data = json.loads(line.strip())
                if 'logs' in json_data:
                    logs_date = json_data['logs'][0:10]
                    if logs_date == YESTERDAY:
                        n_exceptions = json_data.get('n_exceptions', 0)
                        n_failures = json_data.get('n_failures', 0)
                        n_warnings = json_data.get('n_warnings', 0)
                        if n_exceptions > 0 or n_failures > 0 or n_warnings > 0:
                            affected_test_reports.append(json_data)
    return affected_test_reports


def process_reports(params: dict):
    test_reports_folder = CONFIG['folders']['test_reports']
    for filename in [f[:-6] for f in os.listdir(test_reports_folder) if f.endswith('.jsonl')]:
        file_path = os.path.join(test_reports_folder, filename + ".jsonl")
        affected_test_reports = load_affected_test_reports(file_path)
        if len(affected_test_reports) > 0:
            params['payload'] += f"<h2>{filename}</h2>\n"
            for report in affected_test_reports:
                params['payload'] += html_report_from_json(report)


def process():
    logging.info("daily_history.py started.")
    env = Environment(loader=FileSystemLoader('templates'))
    body = env.get_template('daily_history_body.html')
    params = {
        "date": YESTERDAY,
        "dashboard_url": CONFIG['dashboard_url'],
        "payload": ''
    }
    process_reports(params)
    html_str = body.render(params)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html_str)
    logging.info(f"daily_history.py finished: {len(html_str)} chars written to file {OUT_PATH}.")


if __name__ == "__main__":
    process()
