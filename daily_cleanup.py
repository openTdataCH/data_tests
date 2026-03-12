"""A python script which goes through all JSONL (JsonLines) files in the given folder TEST_REPORTS_FOLDER,
and prunes each file, removing lines which are older than a given N days, based on a JSON key "logs",
the value of which contains a timestamp like 2025-12-26T14:27:08.759812+01:00 at the beginning.

"""

import os
import json
import re
from datetime import datetime, timedelta
from configuration import CONFIG
from utilities.file_and_path_utilities import get_path

def prune_old_logs(folder_path, days):
    # Calculate the threshold date
    threshold_date = datetime.now() - timedelta(days=days)

    # Iterate through all files in the specified folder
    for filename in os.listdir(folder_path):
        if filename.endswith('.jsonl'):
            file_path = os.path.join(folder_path, filename)
            pruned_lines = []

            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    if line.strip().startswith('{'):
                        try:
                            log_entry = json.loads(line.strip())
                            # Parse the timestamp
                            log_time = datetime.fromisoformat(log_entry['logs'][0:19])  # timestamp of beginning of first line.

                            # Keep lines newer than the threshold
                            if log_time >= threshold_date:
                                pruned_lines.append(line.strip())
                        except (json.JSONDecodeError, KeyError) as e:
                            print(f"Error processing line in {filename}: {e}")

            # Write pruned lines back to the file
            with open(file_path, 'w', encoding='utf-8') as file:
                newline = ''
                for pruned_line in pruned_lines:
                    file.write(newline + pruned_line)
                    newline = '\n'


def cleanup_by_filename(relative_folder_path, days):
    """ Recursively deletes files in a given path if their filename contains
    a date older than the number of days."""
    root_path = get_path(relative_folder_path)

    if not os.path.exists(root_path):
        print(f"Path not found: {root_path}")
        return
    # Matches dates to date in filename.
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    threshold_date = datetime.now() - timedelta(days=days)

    # Iterate through all mentionned folders recursively and delete files older than threshold
    for current_root, _, files in os.walk(root_path):
        for file_name in files:
            match = date_pattern.search(file_name)
            if not match:
                continue
            try:
                file_date = datetime.strptime(match.group(1), '%Y-%m-%d')
            except ValueError:
                continue
            if file_date < threshold_date:
                full_path = os.path.join(current_root, file_name)
                print(f"Remove old test report: {file_name}")
                os.remove(full_path)

if __name__ == '__main__':
    days = 7  # Replace with the desired number of days
    prune_old_logs(CONFIG['folders']['test_reports'], days)
    cleanup_by_filename(CONFIG['folders']['html'], days)
