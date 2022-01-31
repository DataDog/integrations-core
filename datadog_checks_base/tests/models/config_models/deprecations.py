# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def shared():
    return {'deprecated': {'Release': '8.0.0', 'Migration': 'do this\nand that\n'}}


def instance():
    return {'deprecated': {'Release': '9.0.0', 'Migration': 'do this\nand that\n'}}
