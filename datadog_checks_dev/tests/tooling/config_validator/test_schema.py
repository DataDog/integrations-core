# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev.tooling.config_validator.schema import generate_schema


def test_basic_schema():
    path = os.path.dirname(__file__)
    with open(os.path.join(path, 'test_config_block_1.yaml'), 'r') as f:
        config = f.read()
    schema = generate_schema(config)
    expected = {
        'type': 'object',
        'properties': {
            'instances': {
                'type': 'array',
                'items': {'type': 'object', 'properties': {}, 'additionalProperties': False},
            },
            'init_config': {
                'anyOf': [{'type': 'object', 'properties': {}, 'additionalProperties': False}, {'type': 'null'}]
            },
        },
    }
    assert schema == expected
