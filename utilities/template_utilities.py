"""Support for simple templates.
- Provides a class for handling templates such as XML files or XML fragments with placeholders.
- Loads a file matching the given name (without extension).
- looks for templates in folder ./data/templates   by default
- using placeholders in double curly braces, like {{placeholder_name}}

Usage example:
Template (named my_xml_template.xml):
<xml><name>{{name}}</name><age>{{age}}</age></xml>

Python Code:
from utilities.template_builder import Template
my_xml = Template('my_xml_template')
my_xml.replace('name', 'Alice').replace('age', 66)
print(my_xml)

Output:
<xml><name>Alice</name><age>66</age></xml>

"""

import os

from utilities.file_and_path_utilities import get_path

from configuration import CONFIG

class Template:

    PH_PREFIX, PH_SUFFIX = '{{', '}}'
    DEFAULT_TEMPLATES_FOLDER = CONFIG['folders']['templates']

    def __init__(self, template_name: str, templates_folder: str = DEFAULT_TEMPLATES_FOLDER):
        matches = [f for f in os.listdir(get_path(templates_folder)) if f.startswith(template_name)]
        if len(matches) < 1:
            raise ValueError(f"ERROR: no matching template file {template_name} found in {templates_folder}.")
        if len(matches) > 1:
            raise ValueError(f"ERROR: ambiguous: {len(matches)} matching files {matches} in {templates_folder}.")

        template_file_path = os.path.join(templates_folder, matches[0])

        with open(file=template_file_path, encoding='utf-8', mode='r') as template_file:
            self.template_text = template_file.read()
        self.rendered_text = self.template_text

    def replace(self, placeholder: str, value):
        """Replace the placeholder by a given value."""
        self.rendered_text = self.rendered_text.replace(self.PH_PREFIX + placeholder + self.PH_SUFFIX, str(value))
        return self

    def append(self, placeholder: str, value):
        """Append a value at the given placeholder, leaving the placeholder in place, so that more data may be appended."""
        ph = self.PH_PREFIX + placeholder + self.PH_SUFFIX
        self.rendered_text = self.rendered_text.replace(ph, str(value) + ph)
        return self

    def remove_placeholders(self, text: str):
        """Delete all placeholders"""
        while self.PH_PREFIX in text:
            i1 = text.find(self.PH_PREFIX)
            i2 = text.find(self.PH_SUFFIX, i1 + len(self.PH_PREFIX)) + len(self.PH_SUFFIX)
            text = text[:i1] + text[i2:]
        return text


    def __str__(self):
        return self.remove_placeholders(self.rendered_text)


    def current_text(self):
        return self.rendered_text