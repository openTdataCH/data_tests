"""Utilities (classes, functions) for file and path handling.

"""

import os

properties = {}


def get_path(relative_path: str) -> str:
    """Get the absolute, canonical path to a directory or file, given the relative path respective to the project root."""
    this_module_s_directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.realpath(os.path.join(this_module_s_directory, "..", relative_path))

