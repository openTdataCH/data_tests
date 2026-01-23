"""A python script which goes through all JSONL (JsonLines) files in the given folder TEST_REPORTS_FOLDER,
and prunes each file, removing lines which are older than a given N days, based on a JSON key "logs",
the value of which contains a timestamp like 2025-12-26T14:27:08.759812+01:00 at the beginning.

"""

import os
import json
from datetime import datetime, timedelta
from configuration import CONFIG

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



if __name__ == '__main__':
    days = 7  # Replace with the desired number of days
    prune_old_logs(CONFIG['folders']["test_reports"], days)
