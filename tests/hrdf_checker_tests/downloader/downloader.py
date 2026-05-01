import zipfile

import requests

import os

from utilities.test_utilities import DataTest


class Downloader:
    def __init__(self, download_to_path: str, data_test: DataTest):
        self.data_test = data_test
        self.download_to_path = download_to_path
        try:
            os.mkdir(self.download_to_path)
        except FileExistsError:
            pass

    def fetch_file(self, url, file_name, binary=False):
        response = requests.get(url)
        response.raise_for_status()
        if binary:
            file = open(os.path.join(self.download_to_path, file_name), 'wb')
            file.write(response.content)
        else:
            file = open(os.path.join(self.download_to_path, file_name), 'w', encoding='utf-8')
            file.write(response.text)
        file.close()
        self.data_test.log_info(
            f"Fetched from {url} and written to file {os.path.join(self.download_to_path, file_name)}")

    def extract_zip_to_same_file_name(self, file_name):
        zip_file = zipfile.ZipFile(os.path.join(self.download_to_path, file_name))
        zip_file_infos = zip_file.infolist()
        if len(zip_file_infos) > 1:
            self.data_test.log_warning(
                f"More files in archive {os.path.join(self.download_to_path, file_name)} ({len(zip_file_infos)}) than expected (1)")
        elif len(zip_file_infos) == 0:
            self.data_test.log_failure(
                f"No files in archive {os.path.join(self.download_to_path, file_name)}")
        source_file = zip_file.open(zip_file_infos[0])
        file_content = source_file.read()
        destination_file = open(os.path.join(self.download_to_path, file_name), "wb")
        destination_file.write(file_content)
        source_file.close()
        destination_file.close()
        zip_file.close()
        self.data_test.log_info(f"Extracted file {os.path.join(self.download_to_path, file_name)}")
