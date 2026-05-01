import json
import datetime

from typing_extensions import TypedDict

from utilities.test_utilities import DataTest
import os


class StructuredData(TypedDict):
    date: str
    fahrplan_bezeichung: str
    data: str | dict

class Persister:
    def __init__(self, file_path, data_test: DataTest):
        self.file_path = file_path
        self.data_test = data_test
        try:
            os.mkdir(self.file_path)
            self.data_test.log_info(f"Created directory {self.file_path}")
        except FileExistsError:
            self.data_test.log_info(f"Directory {self.file_path} already exists")

    def persist(self, file_name, content):
        file = open(os.path.join(self.file_path, file_name), "w", encoding="utf-8")
        file.write(json.dumps(content))
        file.close()

    def append_structured_data(self, file_name, data, fahrplan_bezeichnung):
        try:
            original_content: list = self.load(file_name)
        except FileNotFoundError:
            self.data_test.log_info(
                f"Could not append data to file {os.path.join(self.file_path, file_name)} because it doesn't exist")
            original_content = []
        structured_data = {
            "date": datetime.datetime.now().isoformat(),
            "fahrplan_bezeichnung": fahrplan_bezeichnung,
            "data": data,
        }
        if not isinstance(original_content, list):
            raise TypeError(
                f"Data from file {os.path.join(self.file_path, file_name)} must be a list (was {str(type(original_content))} instead), consider deleting the file if the data is no longer needed")
        original_content.append(structured_data)
        self.persist(file_name, original_content)
        self.data_test.log_info(f"Saved data to file {os.path.join(self.file_path, file_name)}")

    def load(self, file_name):
        file = open(os.path.join(self.file_path, file_name), "r", encoding="utf-8")
        content = json.loads(file.read())
        file.close()
        return content

    def get_latest_structured_data(self, file_name) -> StructuredData:
        structured_data = self.load(file_name)
        if not isinstance(structured_data, list):
            raise TypeError(
                f"Data from file {os.path.join(self.file_path, file_name)} must be a list (was {str(type(structured_data))} instead)")
        structured_data.sort(key=lambda x: datetime.datetime.fromisoformat(x["date"]), reverse=True)
        return structured_data[0]
