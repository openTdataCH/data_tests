"""Simple tests of some coderunner"""


import unittest
from utilities.mail_utilities import recipients_that_are_now_is_in_allowed_time_window as r

from datetime import datetime as dt

CONFIG = {
    "Monday": ["07:00", "18:00"],
    "Tuesday": ["07:00", "18:00"],
    "Wednesday": ["07:00", "18:00"],
    "Thursday": ["07:00", "18:00"],
    "Friday": ["07:00", "18:00"],
    "alice@example.com": {
        "Monday": ["09:00", "12:00"],
        "Tuesday": ["09:00", "12:00"],
        "Wednesday": ["09:00", "12:00"],
    },
    "bob@example.com": {
        "Wednesday": ["07:00", "18:00"],
        "Thursday": ["07:00", "18:00"],
        "Friday": ["07:00", "18:00"]
    }
}


M = ["alice@example.com", "bob@example.com", "not.in.config@example.com"]
R_AB0 = M[0] + "," + M[1] + "," + M[2]
R_AB = M[0] + "," + M[1]
R_A0 = M[0] + "," + M[2]
R_B0 = M[1] + "," + M[2]
R_0 = M[2]
R_ = ""


class TestTestRunner(unittest.TestCase):

    def test_case_monday_alice_and_default(self):
        self.assertEqual(r(CONFIG, R_AB0, date_and_time=dt.fromisoformat("2026-03-16T10:09:30")), R_A0)  # Monday

    def test_case_tuesday_alice_and_default(self):
        self.assertEqual(r(CONFIG, R_AB0, date_and_time=dt.fromisoformat("2026-03-17T10:09:00")), R_A0)  # Tuesday

    def test_case_wednesday_all(self):
        self.assertEqual(r(CONFIG, R_AB0, date_and_time=dt.fromisoformat("2026-03-18T10:09:00")), R_AB0)  # Wednesday

    def test_case_thursday_bob_and_default(self):
        self.assertEqual(r(CONFIG, R_AB0, date_and_time=dt.fromisoformat("2026-03-19T10:09:00")), R_B0)  # Thursday

    def test_case_friday_bob_and_default(self):
        self.assertEqual(r(CONFIG, R_AB0, date_and_time=dt.fromisoformat("2026-03-20T10:09:00")), R_B0)  # Friday

    def test_case_sunday_none(self):
        self.assertEqual(r(CONFIG, R_AB0, date_and_time=dt.fromisoformat("2026-03-22T10:09:00")), R_)  # Sunday

    def test_case_monday_afternoon_default(self):
        self.assertEqual(r(CONFIG, R_AB0, date_and_time=dt.fromisoformat("2026-03-16T15:09:00")), R_0)  # Monday afternoon

    def test_case_monday_evening_none(self):
        self.assertEqual(r(CONFIG, R_AB0, date_and_time=dt.fromisoformat("2026-03-16T19:09:00")), R_)  # Monday afternoon

if __name__ == '__main__':
    unittest.main()