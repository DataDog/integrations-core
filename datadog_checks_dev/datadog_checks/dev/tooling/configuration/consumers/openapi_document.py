# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict
from keyword import iskeyword
from typing import List, Tuple

from pydantic import BaseModel

from ..constants import OPENAPI_SCHEMA_PROPERTIES
from ..utils import sanitize_openapi_object_properties

# We don't need any self-documenting features
ALLOWED_TYPE_FIELDS = OPENAPI_SCHEMA_PROPERTIES - {'default', 'description', 'example', 'title'}

# Singleton allowing `None` to be a valid default value
NO_DEFAULT = object()


def build_openapi_document(section: dict, model_id: str, schema_name: str, errors: List[str]):
    """
    :param section: The section on a config spec: ie: init_config or instances
    :param model_id: The model id, which is either 'shared' or 'instance'
    :param schema_name: The specific model class name which is either SharedConfig or InstanceConfig
    :param errors: Array where to write error messages
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

    validator_data = []
    options_seen = set()
    defaults_file_needs_dynamic_values = False
    defaults_file_needs_value_normalization = False
    defaults_file_lines = []
    deprecation_data = defaultdict(dict)

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
            deprecation_data[model_id][option_name] = section_option['deprecation']

        if section_option['required']:
            required_options.append(option_name)
        else:
            (
                option_default_lines,
                needs_value_normalization,
                needs_dynamic_values,
            ) = _get_option_with_default_defintition(model_id, normalized_option_name, type_data)

            defaults_file_lines.extend(option_default_lines)
            defaults_file_needs_dynamic_values += needs_dynamic_values
            defaults_file_needs_value_normalization += needs_value_normalization

        validator_data += _get_type_validators(type_data, option_name, normalized_option_name, errors)

        # Remove fields that aren't part of the OpenAPI specification
        for extra_field in set(type_data) - ALLOWED_TYPE_FIELDS:
            type_data.pop(extra_field, None)

        sanitize_openapi_object_properties(type_data)
    return (
        openapi_document,
        defaults_file_needs_value_normalization,
        defaults_file_needs_dynamic_values,
        defaults_file_lines,
        validator_data,
        deprecation_data,
    )


def _normalize_option_name(option_name):
    # https://github.com/koxudaxi/datamodel-code-generator/blob/0.8.3/datamodel_code_generator/model/base.py#L82-L84
    if iskeyword(option_name) or hasattr(BaseModel, option_name):
        option_name += '_'

    return option_name.replace('-', '_')


def _example_looks_informative(example):
    return '<' in example and '>' in example and example == example.upper()


def _get_default_value(type_data):
    if 'default' in type_data:
        return type_data['default']
    elif 'display_default' in type_data:
        display_default = type_data['display_default']
        if display_default is None:
            return NO_DEFAULT
        else:
            return display_default
    elif 'type' not in type_data or type_data['type'] in ('array', 'object'):
        return NO_DEFAULT

    example = type_data['example']
    if type_data['type'] == 'string':
        if _example_looks_informative(example):
            return NO_DEFAULT
    elif isinstance(example, str):
        return NO_DEFAULT

    return example


def _get_option_with_default_defintition(model_id: str, normalized_option_name: str, type_data: dict):
    """
    Returns as an array of text the function definition that will return the option with a default value.
    :param model_id: 'shared' or 'instance' Used for the function name
    :param normalized_option_name: Used to build the function name
    :type_data: dict containing all the relevant information to build the function
    """
    defaults_file_needs_dynamic_values = False
    defaults_file_needs_value_normalization = False

    defaults_file_lines = ['', '', f'def {model_id}_{normalized_option_name}(field, value):']

    default_value = _get_default_value(type_data)
    if default_value is not NO_DEFAULT:
        defaults_file_needs_value_normalization = True
        defaults_file_lines.append(f'    return {default_value!r}')
    else:
        defaults_file_needs_dynamic_values = True
        defaults_file_lines.append('    return get_default_field_value(field, value)')
    return defaults_file_lines, defaults_file_needs_value_normalization, defaults_file_needs_dynamic_values


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


def _get_type_validators(type_data, option_name, normalized_option_name, errors) -> List[Tuple[str, List]]:
    validator_data = []
    validators = type_data.pop('validators', [])
    if not isinstance(validators, list):
        errors.append(f'Config spec property `{option_name}.value.validators` must be an array')
    elif validators:
        for i, import_path in enumerate(validators, 1):
            if not isinstance(import_path, str):
                errors.append(
                    f'Entry #{i} of config spec property `{option_name}.value.validators` ' f'must be a string'
                )
                break
        else:
            validator_data.append((normalized_option_name, validators))
    return validator_data
