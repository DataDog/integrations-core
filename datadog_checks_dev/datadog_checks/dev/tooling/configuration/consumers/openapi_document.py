# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from keyword import iskeyword
from typing import List

from pydantic import BaseModel

from datadog_checks.dev.tooling.configuration.consumers.model.model_info import ModelInfo

from ..constants import OPENAPI_SCHEMA_PROPERTIES

# We don't need any self-documenting features
ALLOWED_TYPE_FIELDS = OPENAPI_SCHEMA_PROPERTIES - {'default', 'description', 'example', 'title'}


def build_openapi_document(section: dict, model_id: str, schema_name: str, errors: List[str]) -> (dict, ModelInfo):
    """
    :param section: The section on a config spec: ie: init_config or instances
    :param model_id: The model id, which is either 'shared' or 'instance'
    :param schema_name: The specific model class name which is either SharedConfig or InstanceConfig
    :param errors: Array where to write error messages
    :return: openapi_document, model_info
    :rtype: (dict, ModelInfo)
    """
    # We want to create something like:
    #
    # paths:
    #   /instance:
    #     get:
    #       responses:
    #         '200':
    #           content:
    #             application/json:
    #               schema:
    #                 $ref: '#/components/schemas/InstanceConfig'
    # components:
    #   schemas:
    #     InstanceConfig:
    #       required:
    #       - endpoint
    #       properties:
    #         endpoint:
    #           ...
    #         timeout:
    #           ...
    #         ...
    openapi_document = {
        'paths': {
            f'/{model_id}': {
                'get': {
                    'responses': {
                        '200': {
                            'content': {'application/json': {'schema': {'$ref': f'#/components/schemas/{schema_name}'}}}
                        }
                    }
                }
            }
        },
        'components': {'schemas': {}},
    }
    schema = {}
    options = {}
    required_options = []

    schema['properties'] = options
    schema['required'] = required_options
    openapi_document['components']['schemas'][schema_name] = schema

    model_info = ModelInfo()
    options_seen = set()

    for section_option in sorted(section['options'], key=lambda o: (o['name'], o['hidden'])):
        option_name = section_option['name']
        normalized_option_name = _normalize_option_name(option_name)

        if normalized_option_name in options_seen:
            continue
        else:
            options_seen.add(normalized_option_name)

        type_data = _build_type_data(section_option)
        if not type_data:
            errors.append(f'Option `{option_name}` must have a `value` or `options` attribute')
            continue
        options[option_name] = type_data

        if section_option['deprecation']:
            model_info.add_deprecation(model_id, option_name, section_option['deprecation'])

        if section_option['required']:
            required_options.append(option_name)
        else:
            model_info.add_defaults(model_id, normalized_option_name, type_data)

        validator_errors = model_info.add_type_validators(type_data, option_name, normalized_option_name)
        errors.extend(validator_errors)

        # Remove fields that aren't part of the OpenAPI specification
        for extra_field in set(type_data) - ALLOWED_TYPE_FIELDS:
            type_data.pop(extra_field, None)

        _sanitize_openapi_object_properties(type_data)
    return (
        openapi_document,
        model_info,
    )


def _normalize_option_name(option_name):
    # https://github.com/koxudaxi/datamodel-code-generator/blob/0.8.3/datamodel_code_generator/model/base.py#L82-L84
    if iskeyword(option_name) or hasattr(BaseModel, option_name):
        option_name += '_'

    return option_name.replace('-', '_')


def _build_type_data(section_option: dict) -> dict:
    """
    Builds the data structure with the type information (example, default value, nested types...)
    """
    type_data = None
    if 'value' in section_option:
        # Simple type like str, number
        type_data = section_option['value']
    # Some integrations (like `mysql`) have options that are grouped under a top-level option
    elif 'options' in section_option:
        # Object type
        nested_properties = []
        type_data = {'type': 'object', 'properties': nested_properties}
        for nested_option in section_option['options']:
            nested_type_data = nested_option['value']

            # Remove fields that aren't part of the OpenAPI specification
            for extra_field in set(nested_type_data) - ALLOWED_TYPE_FIELDS:
                nested_type_data.pop(extra_field, None)

            nested_properties.append({'name': nested_option['name'], **nested_type_data})
    return type_data


def _sanitize_openapi_object_properties(value):
    if 'anyOf' in value:
        for data in value['anyOf']:
            _sanitize_openapi_object_properties(data)
        return

    value_type = value['type']
    if value_type == 'array':
        _sanitize_openapi_object_properties(value['items'])
    elif value_type == 'object':
        spec_properties = value.pop('properties')
        properties = value['properties'] = {}

        # The config spec `properties` object modifier is not a map, but rather a list of maps with a
        # required `name` attribute. This is so consumers will load objects consistently regardless of
        # language guarantees regarding map key order.
        for spec_prop in spec_properties:
            name = spec_prop.pop('name')
            properties[name] = spec_prop
            _sanitize_openapi_object_properties(spec_prop)

        if 'additionalProperties' in value:
            additional_properties = value['additionalProperties']
            if isinstance(additional_properties, dict):
                _sanitize_openapi_object_properties(additional_properties)
