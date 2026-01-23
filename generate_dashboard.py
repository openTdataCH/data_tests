"""Given a folder TEST_REPORTS_FOLDER containing several files of type JSONL, each with JSON-Line objects,
provide a Python script which generates an HTML report page with a table as follows: For each file,
produce a row; cover the last 7 calendar days in columns of the table; for each day, provide 24 hour subcolumns.
For each JSON object in the file, get the reference timestamp (ISO 8601 formatted) from the the value at the key "logs".
or each hour check if there is one or more objects;
if so, check if object(s) have a "n_exceptions" key with value > 0, then provide a red symbol;
else if object(s) have a "n_failures" key with value > 0, then provide an orange symbol;
else if object(s) have a "n_warnings" key with value > 0, then provide a yellow symbol;
else provide a green symbol

Without using pandas, please.

2025-12-27 -- GPT-4o mini -->
"""


import os
import json
from datetime import datetime, timedelta
from configuration import CONFIG

# Set up date range for the last 7 days
today = datetime.now()
date_range = [today - timedelta(days=i) for i in range(7)]

# Initialize a list to hold data for the report
report_data = []

# Define symbols for each status type
def get_status_symbol(n_exceptions, n_failures, n_warnings):
    if n_exceptions > 0:
        return '🔴'  # Red for exceptions
    elif n_failures > 0:
        return '🟠'  # Orange for failures
    elif n_warnings > 0:
        return '🟡'  # Yellow for warnings
    else:
        return '🟢'  # Green for success

# Process each JSONL file
for filename in os.listdir(CONFIG['folders']["test_reports"]):
    if filename.endswith('.jsonl'):
        file_path = os.path.join(CONFIG['folders']["test_reports"], filename)
        # Initialize a dictionary to hold hour-wise data for this file
        file_data = {date.strftime('%Y-%m-%d'): {hour: "" for hour in range(24)} for date in date_range}

        # Read the JSONL file
        with open(file_path, 'r') as f:
            for line in f:
                json_object = json.loads(line)
                log_time = json_object.get('logs')[0:19]

                if log_time:
                    log_datetime = datetime.fromisoformat(log_time)
                    date_key = log_datetime.strftime('%Y-%m-%d')
                    hour_key = log_datetime.hour

                    # Initialize counts for status
                    n_exceptions = json_object.get('n_exceptions', 0)
                    n_failures = json_object.get('n_failures', 0)
                    n_warnings = json_object.get('n_warnings', 0)

                    # Get status symbol
                    status_symbol = get_status_symbol(n_exceptions, n_failures, n_warnings)

                    # Update the status for the appropriate date and hour
                    if file_data.get(date_key):
                        file_data[date_key][hour_key] = status_symbol

        # Add the file name and aggregated data to the list
        report_data.append((filename, file_data))

# Generate HTML report
html_content = '<html><head><title>Report</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="styles.css"></head><body>'
html_content += '<h1>data_tests_dashboard - Report for the Last 7 Days</h1>'
html_content += '<table border="1"><tr><th>File</th>'

# Create headers for both dates and hours
for date in reversed(date_range):
    html_content += f'<th colspan="24">{date.strftime("%Y-%m-%d")}</th>'
html_content += '</tr><tr><th></th>'

# Create hour columns
for _ in range(7):
    for hour in range(24):
        html_content += f'<th>{hour:02}</th>'
html_content += '</tr>'

# Fill table rows
for file_name, file_data in report_data:
    html_content += f'<tr><td>{file_name}</td>'

    # Fill hourly status for each day
    for date in reversed(date_range):
        date_key = date.strftime('%Y-%m-%d')
        for hour in range(24):
            html_content += f'<td>{file_data[date_key][hour]}</td>'
    html_content += '</tr>'

html_content += '</table></body></html>'

# Write to HTML file
with open(f'{CONFIG['folders']["html"]}/data_tests_dashboard.html', 'w', encoding="utf-8-sig") as report_file:
    report_file.write(html_content)

print("Report generated: data_tests_dashboard.html")
