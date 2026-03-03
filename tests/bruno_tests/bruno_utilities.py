"""Utilities (classes, functions) for tests on Bruno API test-files.

"""

import json
import re
import requests
from utilities.test_utilities import DataTest

class BrunoRunner:
    def __init__(self, path: str, data_test: DataTest):
        self.path = path
        self.data_test = data_test

    def get_path(self):
        return self.path

    def load_raw_file(self):
        try:
            with open(self.get_path(), "r", encoding="utf-8") as raw_file:
                return raw_file.read()
        except Exception as e:
            self.data_test.log_failure(f"Could not read .bru file: {str(e)}")
            return ""

    def extract_block(self, marker: str) -> str:
        """Extract a block from a marker string such as 'body:json'."""
        pattern = rf"{marker}\s*{{(.*?)}}"
        match = re.search(pattern, self.load_raw_file(), re.DOTALL)
        return match.group(1).strip() if match else ""

    def replace_vars(self, text: str, env_vars: dict) -> str:
        """Replace Bruno variables {{var}} with variables from Env-Dict."""
        if not env_vars or not text:
            return text

        for key, value in env_vars.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        return text

    def run(self, env_vars: dict = None) -> (dict, int, DataTest):
        """Run the Bruno test and return (data, size, DataTest)."""
        env_vars = env_vars or {}
        raw_content = self.load_raw_file()

        if self.get_path().endswith("folder.bru"):
            return {}, 0, self.data_test

        url_match = re.search(r"url:\s*(.*)", raw_content, re.IGNORECASE)
        if not url_match:
            self.data_test.log_failure(f"Could not parse URL: {self.get_path()}")
            return {}, 0, self.data_test

        raw_url = url_match.group(1).strip()

        open_brackets = raw_url.count('{{')
        while raw_url.count('}}') > open_brackets or (raw_url.endswith('}') and not raw_url.endswith('}}')):
            raw_url = raw_url[:-1].strip()

        if raw_url.endswith('}') and not raw_url.endswith('}}'):
            raw_url = raw_url.rstrip('}')

        method_match = re.search(r"^(\w+)\s*\{", raw_content, re.MULTILINE)
        method = method_match.group(1).upper() if method_match else "POST"

        url = self.replace_vars(raw_url, env_vars)
        if "{{" in url:
            self.data_test.log_warning(f"Not all variables were replaced: {url}")

        headers = {}
        headers_raw = self.extract_block("headers")
        if headers_raw:
            headers_replaced = self.replace_vars(headers_raw, env_vars)
            for line in headers_replaced.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip()] = value.strip()
        auth_bearer_raw = self.extract_block("auth:bearer")
        if auth_bearer_raw:
            token_match = re.search(r"BearerToken:\s*(.*)", auth_bearer_raw, re.IGNORECASE)
            if token_match:
                raw_token = token_match.group(1).strip()
                token_value = self.replace_vars(raw_token, env_vars)
                if "{{" in token_value:
                    self.data_test.log_warning(f"Token-Variable wurde NICHT ersetzt: {token_value}")

                headers["Authorization"] = f"Bearer {token_value}"

        body_raw = self.extract_block("body:json")
        body_data = None
        if body_raw:
            try:
                body_raw_replaced = self.replace_vars(body_raw, env_vars)
                body_data = json.loads(body_raw_replaced)
            except json.JSONDecodeError:
                self.data_test.log_failure(f"Could not parse JSON body in {self.get_path()}")

        try:
            if not url or url.startswith("{{"):
                raise ValueError(f"Invalid URL after replacement of variables: '{url}'")

            response = requests.request(
                method=method,
                url=url,
                json=body_data,
                headers=headers,
                timeout=30
            )

            size = len(response.content)

            try:
                res_data = response.json()
            except:
                res_data = {"raw": response.text}

            return res_data, size, self.data_test

        except Exception as e:
            self.data_test.log_failure(f"Could not execute test: {str(e)}")
            return {}, 0, self.data_test