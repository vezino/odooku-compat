import os.path
import json
import importlib


ODOOKU_JSON_FILE = os.path.abspath('odooku.json')
project_addons = []


def load_projects():
    odooku_json = {}
    if os.path.isfile(ODOOKU_JSON_FILE):
        with open(ODOOKU_JSON_FILE) as f:
            odooku_json = json.load(f)

    for module_name in odooku_json.get('odooku', {}).get('projects', []):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            # For now be explit..
            raise

        # Look for addons folder in module package
        addons_path = os.path.join(os.path.dirname(module.__file__), 'addons')
        if os.path.isdir(addons_path):
            project_addons.append(addons_path)
