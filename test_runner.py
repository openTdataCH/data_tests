"""Script to run and manage any of the tests in the tests subfolder.

Can be called by a cron job, bash script or on the command line.
In this way, runs as an independent Python application (OS process).

These 2 arguments must be passed: 1. test name - 2. alert group (defined in the configuration.py)..

The test runner does these main steps:
1. imports the desired test, calls its run() method, passing the CONFIG dict to it
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
import os

from configuration import get_prop, CONFIG
from utilities.mail_utilities import send_mail
from utilities.template_utilities import Template
from utilities.test_utilities import DataTest, html_report_from_json

LOG_FILE = os.path.join(CONFIG['folders']['logs'], "test_runner.log")
logging.basicConfig(handlers=[logging.FileHandler(LOG_FILE, 'a', 'utf-8')], level=logging.INFO, format='%(asctime)s: %(levelname)s: %(message)s')


def get_commandline_arguments():
    if len(sys.argv) < 2:
        raise ValueError("run_test.py requires 2 parameters: test name and alert group.")

    test_name = sys.argv[1]
    test_name = test_name[:-3] if test_name.endswith(".py") else test_name
    alert_group = sys.argv[2]
    return test_name, alert_group


def import_and_run_test(test_name: str) -> dict:
    test_report = DataTest(test_name)
    test_module_path = f"{CONFIG['folders']['tests']}.{test_name}"
    try:
        test_module = importlib.import_module(test_module_path)
        if hasattr(test_module, 'run') and callable(getattr(test_module, 'run')):
            test_run_function = getattr(test_module, 'run')
            signature = inspect.signature(test_run_function)
            if 'config' in signature.parameters:  # if it has a config parameter, hand over the CONFIG to it.
                test_report = test_run_function(config=copy.deepcopy(CONFIG))  # copy to avoid updates
            else:  # if not, try to run the test anyway, without parameters.
                test_report = test_run_function()
        else:
            raise ValueError(f"No callable function 'run()' found in {test_module_path}, cannot run test.")
    except Exception as e:
        error_message = f"Test run of {test_name} failed with Exception: {str(e)}"
        test_report.log_exception(error_message, exception=e)
        logging.error(error_message)

    test_report_dict = test_report.to_dict() if isinstance(test_report, DataTest) else dict(test_report)

    return test_report_dict


def store_test_report(test_name: str, test_report: dict):
    path = f"{CONFIG['folders']['test_reports']}/{test_name}.jsonl"
    with open(path, "a", encoding='utf-8') as f:
        f.write('\n' + json.dumps(test_report, ensure_ascii=False))


def has_exceptions_or_failures(test_report: dict) -> bool:
    for count in "n_exceptions", "n_failures":
        v = test_report.get(count)
        if v is not None and v > 0:
            return True
    return False


def if_errors_send_alert_mail(test_name: str, alert_group: str, test_report: dict):
    if has_exceptions_or_failures(test_report):
        subject = f"data_tests: test '{test_name}' has errors or failures"
        recipients = get_prop("skiplus_support")
        body = Template("daily_report_mail_body.html")
        body.replace("subject", subject).replace("name", test_name)
        body.append("payload", html_report_from_json(test_report))
        return_code, message = send_mail(subject, recipients, body)
        if return_code != 0:
            raise ConnectionError(f"send_mail() has an error: return_code={return_code}, message={message}!")


if __name__ == "__main__":
    test_name, alert_group = get_commandline_arguments()
    logging.info(f"test_runner.py {test_name} {alert_group} - started.")
    try:
        test_report = import_and_run_test(test_name)
        store_test_report(test_name, test_report)
        if_errors_send_alert_mail(test_name, alert_group, test_report)
        logging.info(f"test_runner.py {test_name} {alert_group} - finished.")
    except Exception as e:
        logging.error(f"test_runner.py {test_name} {alert_group} - failed with Exception: {str(e)}")
