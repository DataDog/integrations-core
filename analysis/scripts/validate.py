"""Tiny JSON-Schema-draft-07 subset validator (stdlib only).

Supports: type, enum, required, additionalProperties (false only),
properties, items, pattern. Sufficient for analysis/schema.json.
"""
import json
import re
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema.json"


def _type_ok(value, expected):
    if isinstance(expected, list):
        return any(_type_ok(value, t) for t in expected)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "null":
        return value is None
    return True


def _validate(value, schema, path, errors):
    if "type" in schema and not _type_ok(value, schema["type"]):
        errors.append(f"{path}: expected {schema['type']}, got {type(value).__name__}")
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in {schema['enum']}")
    if "pattern" in schema and isinstance(value, str):
        if not re.search(schema["pattern"], value):
            errors.append(f"{path}: {value!r} does not match {schema['pattern']!r}")
    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required field {req!r}")
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}))
            for k in value:
                if k not in allowed:
                    errors.append(f"{path}: unknown field {k!r}")
        for k, sub in schema.get("properties", {}).items():
            if k in value:
                _validate(value[k], sub, f"{path}.{k}", errors)
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            _validate(item, schema["items"], f"{path}[{i}]", errors)


def validate(payload, schema):
    errors = []
    _validate(payload, schema, "$", errors)
    return errors


def main():
    if len(sys.argv) != 2:
        print("usage: validate.py <file.json>", file=sys.stderr)
        sys.exit(2)
    schema = json.loads(SCHEMA_PATH.read_text())
    payload = json.loads(Path(sys.argv[1]).read_text())
    errors = validate(payload, schema)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
