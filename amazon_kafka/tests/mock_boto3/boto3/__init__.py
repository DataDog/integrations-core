# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os


def client(*args, **kwargs):
    return Client(*args, **kwargs)


class Client(object):
    def __init__(self, *args, **kwargs):
        super(Client, self).__init__()

    def list_nodes(self, *args, **kwargs):
        fixture = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'list_nodes.json')
        with open(fixture, 'rb') as f:
            return json.loads(f.read().decode('utf-8'))
