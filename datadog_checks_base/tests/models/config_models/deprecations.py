# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def shared():
    return {'deprecated': {'Agent_Version': '8.0.0', 'Migration': 'do this\nand that\n'}}


def instance():
    return {'deprecated': {'Agent version': '9.0.0', 'Migration': 'do this\nand that\n'}}
