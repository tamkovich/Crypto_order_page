import json


def read_config():
    with open('config_test.json', 'r') as f:
        return json.load(f)
