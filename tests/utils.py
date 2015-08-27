import json


def copy(d):
    return json.loads(json.dumps(d))
