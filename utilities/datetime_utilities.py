"""Utilities (classes, functions) for handling date and time related tasks.

"""
import pytz
from datetime import datetime as dt, timezone


def age_in_days(iso8601_timestamp: str) -> float:
    """The age of a given timestam (date and time), i.e. with respect to now; raises ValueError if it fais."""
    try:
        if not(iso8601_timestamp.endswith("Z") or '+' in iso8601_timestamp):  # if TZ hint like '+01:00' missing, add it:
            iso8601_timestamp = iso8601_timestamp + dt.now(pytz.timezone('Europe/Zurich')).isoformat()[26:]
        then = dt.fromisoformat(iso8601_timestamp)
        now = dt.now(timezone.utc)
        age = now - then
        age_d = age.days + age.seconds / 86400.0
        return age_d
    except Exception as e:
        raise ValueError(f"age_in_days() for {iso8601_timestamp} fails with error: {e}")