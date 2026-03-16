"""Script to run and manage any of the tests in the tests subfolder.

Can be called by a cron job, bash script or on the command line.
In this way, runs as an independent Python application (OS process).

These 2 arguments must be passed: 1. test name - 2. alert group (defined in the configuration.py)..

The test runner does these main steps:
1. imports the desired tests.py module, calls its run() method, passing the CONFIG and variant to it if available.
2. waits for its repsonse, which should be a test report dict or TestReport object.
3. stores the test report at TEST_REPORTS_FOLDER.
4. if the test has errors, it immediately sends an e-mail to the given alert group.
"""

import sys

import copy
import importlib
import inspect
import json
import logging

from configuration import get_prop, CONFIG
from utilities.mail_utilities import send_mail, recipients_that_are_now_is_in_allowed_time_window
from utilities.template_utilities import Template
from utilities.test_utilities import DataTest, html_report_from_json
from datetime import datetime as dt

LOG_FILE = "data/logs/test_runner.log"
logging.basicConfig(handlers=[logging.FileHandler(LOG_FILE, 'a', 'utf-8')], level=logging.INFO, format='%(asctime)s: %(levelname)s: %(message)s')


def get_commandline_arguments():
    if len(sys.argv) < 2:
        raise ValueError("run_test.py requires 2 parameters: test name and alert group.")

    name_and_variant = sys.argv[1]
    name_and_variant = name_and_variant[:-3] if name_and_variant.endswith(".py") else name_and_variant
    alert_group = sys.argv[2]
    return name_and_variant, alert_group


def import_and_run_test(name_and_variant: str) -> dict:
    nv_list = name_and_variant.split("/")
    name = nv_list[0] if len(nv_list) > 1 else name_and_variant
    variant = nv_list[1] if len(nv_list) > 1 else None
    normalized_name = f"{name}_{variant}" if variant else name
    test_report = DataTest(normalized_name)
    try:
        test_module_path = f"tests.{name}.test"
        test_module = importlib.import_module(test_module_path)
        if hasattr(test_module, 'run') and callable(getattr(test_module, 'run')):
            test_run_function = getattr(test_module, 'run')
            signature = inspect.signature(test_run_function)
            if 'config' in signature.parameters:
                config_copy = copy.deepcopy(CONFIG)  # copy to avoid updates
                if 'variant' in signature.parameters:
                    test_report = test_run_function(config=config_copy, variant=variant)
                else:
                    test_report = test_run_function(config=config_copy)  # copy to avoid updates
            else:
                if 'variant' in signature.parameters:
                    test_report = test_run_function(variant=variant)
                else:
                    test_report = test_run_function()
        else:
            raise ValueError(f"No callable function 'run()' found in {test_module_path}, cannot run test.")
    except Exception as e:
        error_message = f"Test run of {name_and_variant} failed with Exception: {str(e)}"
        test_report.log_exception(error_message, exception=e)
        logging.error(error_message)

    test_report_dict = test_report.to_dict() if isinstance(test_report, DataTest) else dict(test_report)

    return test_report_dict


def store_test_report(name_and_variant: str, test_report: dict):
    path = f"data/test_reports/{name_and_variant.replace('/', '_')}.jsonl"
    with open(path, "a", encoding='utf-8') as f:
        f.write('\n' + json.dumps(test_report, ensure_ascii=False))


def has_exceptions_or_failures(test_report: dict) -> bool:
    for count in "n_exceptions", "n_failures":
        v = test_report.get(count)
        if v is not None and v > 0:
            return True
    return False



def if_errors_send_alert_mail(name_and_variant: str, alert_group: str, test_report: dict):
    if has_exceptions_or_failures(test_report):
        recipients = get_prop("skiplus_support")
        allowed_recipients = recipients_that_are_now_is_in_allowed_time_window(get_prop("test_runner_alerts_allowed_times"), recipients)
        if allowed_recipients:
            subject = f"data_tests: test '{name_and_variant}' has errors or failures"
            body = Template("daily_report_mail_body.html")
            body.replace("subject", subject).replace("name", name_and_variant)
            body.append("payload", html_report_from_json(test_report))
            return_code, message = send_mail(subject, allowed_recipients, body)
            if return_code != 0:
                raise ConnectionError(f"send_mail() has an error: return_code={return_code}, message={message}!")


if __name__ == "__main__":
    name_and_variant, alert_group = get_commandline_arguments()
    logging.info(f"test_runner.py {name_and_variant} {alert_group} - started.")
    try:
        test_report = import_and_run_test(name_and_variant)
        store_test_report(name_and_variant, test_report)
        if_errors_send_alert_mail(name_and_variant, alert_group, test_report)
        logging.info(f"test_runner.py {name_and_variant} {alert_group} - finished.")
    except Exception as e:
        logging.error(f"test_runner.py {name_and_variant} {alert_group} - failed with Exception: {str(e)}")
