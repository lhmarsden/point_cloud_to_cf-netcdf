import json
import os
import yaml

class GlobalAttributes:

    def __init__(self):
        self.data = None

    def read_global_attributes(self, arg):
        """Determine if the argument is a file path (YAML) or a JSON string and read global attributes accordingly."""
        if os.path.isfile(arg):
            self.dict = self._read_from_yaml_file(arg)
        else:
            self.dict = self._read_from_json_string(arg)

    def _read_from_yaml_file(self, filepath):
        """Read global attributes from a YAML file."""
        with open(filepath, 'r') as file:
            return yaml.safe_load(file)

    def _read_from_json_string(self, json_string):
        """Parse JSON string."""
        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            raise ValueError('Invalid JSON data.')