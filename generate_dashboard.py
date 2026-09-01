"""Given a folder TEST_REPORTS_FOLDER containing several files of type JSONL, each with JSON-Line objects,
provide a Python script which generates an HTML report page with a table as follows: For each file,
produce a row; cover the last DAY_RANGE calendar days in columns of the table; for each day, provide 24 hour subcolumns.
For each JSON object in the file, get the reference timestamp (ISO 8601 formatted) from the value at the key "logs".
or each hour check if there is one or more objects;
if so, check if object(s) have a "n_exceptions" key with value > 0, then provide a red symbol;
else if object(s) have a "n_failures" key with value > 0, then provide an orange symbol;
else if object(s) have a "n_warnings" key with value > 0, then provide a yellow symbol;
else provide a green symbol

"""

import os
import json
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader
from configuration import CONFIG

DAY_RANGE = 3
HTML_OUT_DIR = CONFIG['folders']['html']

env = Environment(loader=FileSystemLoader('templates'))
main_template = env.get_template('dashboard_template.html')
detail_template = env.get_template('detail_template.html')

def get_status(obj):
    if obj.get('n_exceptions', 0) > 0: return 'exception'
    if obj.get('n_failures', 0) > 0: return 'failure'
    if obj.get('n_warnings', 0) > 0: return 'warning'
    return 'ok'

def get_worst_status(status_list):
    hierarchy = {'exception': 3, 'failure': 2, 'warning': 1, 'ok': 0}
    return max(status_list, key=lambda s: hierarchy.get(s, 0)) if status_list else 'white'

def escape_html(text):
    """Ersetzt HTML-Sonderzeichen manuell."""
    return text.replace('&', '&amp;') \
        .replace('<', '&lt;') \
        .replace('>', '&gt;') \
        .replace('"', '&quot;') \
        .replace("'", '&#39;')

def prepare_log_content(content):
    lines = content.split('\n')
    processed_lines = []

    replacements = {
        'EXCEPTION': '<span class="hl-exception">EXCEPTION</span>',
        'ERROR': '<span class="hl-exception">ERROR</span>',
        'FAILURE': '<span class="hl-failure">FAILURE</span>',
        'FAILED': '<span class="hl-failure">FAILED</span>',
        'WARNING': '<span class="hl-warning">WARNING</span>',
    }

    for line in lines:
        safe_line = escape_html(line)
        words = safe_line.split()
        new_words = []
        for word in words:
            if word.startswith('http://') or word.startswith('https://'):
                new_words.append(f'<a href="{word}" target="_blank">{word}</a>')
            else:
                new_words.append(word)
        line_content = ' '.join(new_words)
        for term,replacement in replacements.items():
            line_content = line_content.replace(term, replacement)
        processed_lines.append(line_content)

    return '<br>'.join(processed_lines)

def get_stats_summary(obj):
    exc = obj.get('n_exceptions', 0)
    fail = obj.get('n_failures', 0)
    warn = obj.get('n_warnings', 0)
    return f"{exc} exceptions, {fail} failures, {warn} warnings."

def generate_dashboard():
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    date_range = [today - timedelta(days=i) for i in range(DAY_RANGE)]

    raw_grouped = {}
    if not os.path.exists(HTML_OUT_DIR):
        os.makedirs(HTML_OUT_DIR)

    for filename in [f for f in sorted(os.listdir(CONFIG['folders']['test_reports'])) if f.endswith('.jsonl')]:

        test_id = filename.replace('.jsonl', '')

        # create category if test contains variants to create an accordion
        delimiter = "tests"
        if delimiter in test_id.lower():
            parts = test_id.lower().split(delimiter)
            category = parts[0].strip("_")
            start_index = test_id.lower().find(delimiter) + len(delimiter)
            display_name = test_id[start_index:].strip("_")
            if not display_name:
                display_name = category
        else:
            category = "GENERAL"
            display_name = test_id.strip("_")

        file_path = os.path.join(CONFIG['folders']['test_reports'], filename)

        file_stats = {d.strftime('%Y-%m-%d'): {h: [] for h in range(24)} for d in date_range}

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    log_time_str = obj.get('logs', '')[:19]
                    log_content = obj.get('logs')
                    if not log_time_str: continue

                    dt = datetime.fromisoformat(log_time_str)
                    d_key = dt.strftime('%Y-%m-%d')
                    h_key = dt.hour

                    if d_key in file_stats:
                        file_stats[d_key][h_key].append({
                            'time': dt.strftime('%H:%M:%S'),
                            'status': get_status(obj),
                            'stats_summary': get_stats_summary(obj),
                            'content': prepare_log_content(log_content)})
                except Exception:
                    continue

        # Detail pages
        test_final_stats = {}
        test_subfolder = os.path.join(HTML_OUT_DIR, test_id)
        if not os.path.exists(test_subfolder):
            os.makedirs(test_subfolder)

        for d_key, hours in file_stats.items():
            test_final_stats[d_key] = {}
            for h_key, runs in hours.items():
                if runs:
                    worst_status = get_worst_status([r['status'] for r in runs])
                    detail_fn = f"details_{test_id}_{d_key}T{h_key:02}.html"

                    full_detail_path = os.path.join(test_subfolder, detail_fn)

                    relative_link = f"{test_id}/{detail_fn}"

                    with open(full_detail_path, 'w', encoding='utf-8') as df:
                        df.write(detail_template.render(
                            test_name=test_id,
                            timestamp=f"{d_key} {h_key:02}:00 - {h_key:02}:59",
                            runs=runs
                        ))
                    test_final_stats[d_key][h_key] = {
                        'status': worst_status,
                        'count': len(runs),
                        'link': relative_link
                    }
                else:
                    test_final_stats[d_key][h_key] = None

        if category not in raw_grouped:
            raw_grouped[category] = []

        raw_grouped[category].append({
            'name': display_name,
            'full_id': test_id,
            'stats': test_final_stats
        })

    # create final structure and collect categories
    grouped_data_final = {}

    for category, tests in raw_grouped.items():
        cat_summary_accumulator = {d.strftime('%Y-%m-%d'): {h: [] for h in range(24)} for d in date_range}

        for t in tests:
            for d_key, hours in t['stats'].items():
                for h_key, data in hours.items():
                    if data:
                        cat_summary_accumulator[d_key][h_key].append(data['status'])

        category_summary = {}
        for d_key, hours in cat_summary_accumulator.items():
            category_summary[d_key] = {}
            for h_key, statuses in hours.items():
                if statuses:
                    worst_status = get_worst_status(statuses)
                    target_link = None
                    for test in tests:
                        if test['stats'][d_key][h_key] and test['stats'][d_key][h_key]['status'] == worst_status:
                            target_link = test['stats'][d_key][h_key]['link']
                            break
                    category_summary[d_key][h_key] = {
                        'status': worst_status,
                        'link': target_link
                    }
                else:
                    category_summary[d_key][h_key] = None

        grouped_data_final[category] = {
            'tests': tests,
            'summary': category_summary
        }

    output = main_template.render(
        grouped_data=grouped_data_final,
        date_range=date_range,
        now=datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    )

    dashboard_path = os.path.join(HTML_OUT_DIR, 'data_tests_dashboard.html')
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(output)

if __name__ == "__main__":
    generate_dashboard()
