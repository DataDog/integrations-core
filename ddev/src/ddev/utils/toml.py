# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def load_toml_data(data):
    return tomllib.loads(data)


def load_toml_file(path):
    with open(path, encoding='utf-8') as f:
        return tomllib.loads(f.read())


def dump_toml_data(data, path):
    import tomli_w

    with open(path, "wb") as f:
        tomli_w.dump(data, f)
