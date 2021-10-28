# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def default_option_example(option_name):
    return f'<{option_name.upper()}>'


def normalize_source_name(source_name):
    return source_name.lower().replace(' ', '_')


def sanitize_openapi_object_properties(value):
    if 'anyOf' in value:
        for data in value['anyOf']:
            sanitize_openapi_object_properties(data)

        return

    value_type = value['type']
    if value_type == 'array':
        sanitize_openapi_object_properties(value['items'])
    elif value_type == 'object':
        spec_properties = value.pop('properties')
        properties = value['properties'] = {}

        # The config spec `properties` object modifier is not a map, but rather a list of maps with a
        # required `name` attribute. This is so consumers will load objects consistently regardless of
        # language guarantees regarding map key order.
        for spec_prop in spec_properties:
            name = spec_prop.pop('name')
            properties[name] = spec_prop
            sanitize_openapi_object_properties(spec_prop)

        if 'additionalProperties' in value:
            additional_properties = value['additionalProperties']
            if isinstance(additional_properties, dict):
                sanitize_openapi_object_properties(additional_properties)
