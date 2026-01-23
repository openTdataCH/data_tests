"""Utilities (classes, functions) for supporting automated data quality tests.

Includes the definition of the DataTest class, which serves to handle a test with its logs and report data.

"""

import pytz
from datetime import datetime as dt


def now_iso8601():
    return dt.now(pytz.timezone('Europe/Zurich')).isoformat()


class DataTest():

    def __init__(self, name: str):
        self.name = name
        self.logs = []
        self.n_warnings = 0
        self.n_failures = 0
        self.exceptions = []
        self.summary = "initial"
        self.log_info(f"Test '{self.name}' started.")

    def _log(self, text: str, level: str, exception = None):
        self.logs.append(f"{now_iso8601()}: {level:9}: " + text)
        if level == "WARNING":
            self.n_warnings += 1
        if level == "FAILURE":
            self.n_failures += 1
        if exception:
            self.exceptions.append(exception)

    def log_info(self, text: str, summary = None):
        self._log(text, level='info')

    def log_warning(self, text: str, summary = None):
        self._log(text, level='WARNING')

    def log_failure(self, text: str):
        self._log(text, level='FAILURE')

    def log_exception(self, text: str, exception = None):
        self._log(text, level='EXCEPTION', exception=exception)

    def test(self, condition: bool, if_true_log_info: str=None, if_false_log_warning: str=None, if_false_log_failure: str=None) -> bool:
        """Test a condition (bool); if true, log an info, if false log warning and/or failure. Returns the bool of the condition."""
        if condition:
            if if_true_log_info:
                self.log_info(if_true_log_info)
        else:
            if if_false_log_warning:
                self.log_warning(if_false_log_warning)
            if if_false_log_failure:
                self.log_failure(if_false_log_failure)
        return condition

    def to_dict(self) -> dict:
        self.log_info(f"Test report summary: EXCEPTIONS={len(self.exceptions)}, FAILURES={self.n_failures}, WARNINGS={self.n_warnings}.")
        return {
            "name": self.name,
            "logs": "\n".join(self.logs),
            "n_warnings": self.n_warnings,
            "n_failures": self.n_failures,
            "n_exceptions": len(self.exceptions),
            "exceptions": str(self.exceptions)
        }

    def ignore(self):
        pass

    def __str__(self):
        s = (f"TestReport for test '{self.name}':\n"
             f"  - n_exceptions: {len(self.exceptions)}\n"
             f"  - n_failures  : {self.n_failures}\n"
             f"  - n_warnings  : {self.n_warnings}\n"
             f"  - exceptions  : {str(self.exceptions)}\n"
             f"Logs:\n  > ")
        s += "\n  > ".join(self.logs)
        return s



if __name__ == "__main__":
    print(f"{__file__}: Simple tests")
    tr = DataTest("test1")

    d = tr.to_dict()
    assert d['name'] == 'test1'
    assert d["n_warnings"] == 0
    assert d["n_failures"] == 0
    assert d["n_exceptions"] == 0
    assert len(d["logs"].splitlines()) == 2
    assert 'started' in d["logs"]

    tr.log_warning("added a warning.")
    d = tr.to_dict()
    assert d["n_warnings"] == 1
    assert d["n_failures"] == 0
    assert d["n_exceptions"] == 0
    assert len(d["logs"].splitlines()) == 4

    tr.log_failure("added a failed test.")
    d = tr.to_dict()
    assert d["n_warnings"] == 1
    assert d["n_failures"] == 1
    assert d["n_exceptions"] == 0
    assert len(d["logs"].splitlines()) == 6

    tr.log_exception("added an exception.", exception=ValueError("an error"))
    d = tr.to_dict()
    assert d["n_warnings"] == 1
    assert d["n_failures"] == 1
    assert d["n_exceptions"] == 1
    assert len(d["logs"].splitlines()) == 8

    print(d["logs"])
    print(d)
    print("passed all tests")
