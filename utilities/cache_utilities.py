"""Utilities (classes, functions) for storing cached data.

"""
import json
import os
import shutil
import pathlib


CACHE_PATH = f'../data/persistent_test_data/'


def load_json_from_cache_if_exists(directory: str, filename: str) -> dict:
    dir_path = os.path.join(CACHE_PATH, directory)
    try:
        pathlib.Path(dir_path).mkdir(parents=True, exist_ok=True)
        file_path = os.path.join(dir_path, filename)
        with open(file_path, encoding='utf-8') as json_file:
            data = json.load(json_file)
            return data
    except Exception:
        return None


def save_json_to_cache(directory: str, filename: str, data: dict):
    dir_path = os.path.join(CACHE_PATH, directory)
    pathlib.Path(dir_path).mkdir(parents=True, exist_ok=True)
    file_path = os.path.join(dir_path, filename)
    with open(file_path, encoding='utf-8', mode='w') as json_file:
        json_file.write(json.dumps(data, indent=4, sort_keys=True))



if __name__ == '__main__':
    print("a simple test:")
    data1 = {"test": "simple test with ööü", "test2": {"nested": "data"}}
    save_json_to_cache("cache_utilities_simple_test", 'test.json', data1)
    data2 = load_json_from_cache_if_exists("cache_utilities_simple_test", 'test.json')
    assert data1 == data2
    print("simple test done sucessfully.")
