import csv
import os

from utilities.test_utilities import DataTest


class CSVParser:
    def __init__(self, csv_file_path, data_test: DataTest):
        self.csv_file_path = csv_file_path
        self.data_test = data_test

    def read_as_dict(self):
        file = open(self.csv_file_path, "r", encoding="utf-8-sig")
        output_dict = list(csv.DictReader(file, delimiter=";"))
        file.close()
        return output_dict

    def close(self, delete_csv_file: bool = True) -> None:
        if delete_csv_file:
            os.remove(self.csv_file_path)
            self.data_test.log_info(f"Removed csv file {self.csv_file_path}")
