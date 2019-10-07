# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .validator import _parse_for_config_blocks, _parse_init_config, get_end_of_part


def type_to_schema(type_name):
    if type_name in ('integer', 'boolean', 'string', 'object'):
        return type_name
    if type_name in ('float', 'double'):
        return 'number'
    if type_name == 'dictionary':
        return 'object'
    if type_name.startswith('list'):
        return 'array'
    raise TypeError('Unknown type %s' % type_name)


def schema_builder(blocks):
    result = {}
    for block in blocks:
        if block.param_prop is None:
            continue
        result[block.param_prop.var_name] = {'type': type_to_schema(block.param_prop.type_name)}
    return result


def generate_schema(config):
    config_lines = config.split('\n')
    init_config_line = -1
    instances_line = -1
    for i, line in enumerate(config_lines):
        if line.startswith('init_config:'):
            init_config_line = i
        if line.startswith('instances:'):
            instances_line = i
    instances_end = get_end_of_part(config_lines, instances_line)

    init_blocks = _parse_init_config(config_lines, init_config_line, [])
    instance_blocks = _parse_for_config_blocks(config_lines, instances_line + 1, instances_end, [])

    init_config_schema = schema_builder(init_blocks)
    instances_schema = schema_builder(instance_blocks)
    schema = {
        'type': 'object',
        'properties': {
            'init_config': {
                'anyOf': [
                    {'type': 'object', 'properties': init_config_schema, 'additionalProperties': False},
                    {'type': 'null'},
                ]
            },
            'instances': {
                'type': 'array',
                'items': {'type': 'object', 'properties': instances_schema, 'additionalProperties': False},
            },
        },
    }
    return schema
