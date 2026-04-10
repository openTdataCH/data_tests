"""Utilities (classes, functions) for file and path handling.

"""

import os

from pathlib import Path
from datetime import datetime, timezone


def get_path(relative_path: str) -> str:
    """Get the absolute, canonical path to a directory or file, given the relative path respective to the project root."""
    this_module_s_directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.realpath(os.path.join(this_module_s_directory, "..", relative_path))


def file_age_in_days_if_exists(relative_path: str) -> float:
    """a python function which checks if a file at a given path exists, and if it does, returns its age in days, else returns None."""
    p = Path(get_path(relative_path))
    if not p.exists():
        return None
    # Use modification time (epoch) in UTC
    mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
    now = datetime.now(tz=timezone.utc)
    age_seconds = (now - mtime).total_seconds()
    return age_seconds / 86400.0



if __name__ == "__main__":
    print(f"{__file__}: simple tests")
