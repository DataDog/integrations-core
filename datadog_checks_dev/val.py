# Example to show how to validate a config
# python val.py conf.schema conf.yaml
import json
import sys

import yaml
from jsonschema import validate


def main():
    schema = sys.argv[1]
    conf = sys.argv[2]

    with open(schema) as f:
        schema = f.read()

    with open(conf) as f:
        conf = f.read()

    schema = json.loads(schema)
    conf = yaml.safe_load(conf)
    validate(instance=conf, schema=schema)


if __name__ == "__main__":
    main()
