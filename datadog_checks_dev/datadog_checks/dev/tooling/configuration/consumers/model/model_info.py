# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict
from typing import List

# Singleton allowing `None` to be a valid default value
NO_DEFAULT = object()


class ModelInfo:
    def __init__(self):
        self.defaults_file_needs_value_normalization = False
        self.defaults_file_needs_dynamic_values = False
        # Contains function definitions as text for options that are optional so they have a default value
        self.defaults_file_lines: List[str] = []
        self.validator_data = []
        self.deprecation_data = defaultdict(dict)

    def update(self, section_model):
        """
        Updates this model with another ModelInfo
        """
        self.defaults_file_needs_value_normalization += section_model.defaults_file_needs_value_normalization
        self.defaults_file_needs_dynamic_values += section_model.defaults_file_needs_dynamic_values
        self.defaults_file_lines.extend(section_model.defaults_file_lines)
        self.validator_data.extend(section_model.validator_data)
        self.deprecation_data.update(section_model.deprecation_data)

    def add_type_validators(self, type_data: dict, option_name: str, normalized_option_name: str) -> List[str]:
        """
        :param type_data: dict with the option type information
        :param option_name: The option name
        :param normalized_option_name: Normalized option name
        :returns: A list of errors
        """
        validator_data = []
        errors = []
        validators = type_data.pop('validators', [])
        if not isinstance(validators, list):
            errors.append(f'Config spec property `{option_name}.value.validators` must be an array')
        elif validators:
            for i, import_path in enumerate(validators, 1):
                if not isinstance(import_path, str):
                    errors.append(
                        f'Entry #{i} of config spec property `{option_name}.value.validators` must be a string'
                    )
                    break
            else:
                validator_data.append((normalized_option_name, validators))
        self.validator_data += validator_data
        return errors

    def add_deprecation(self, model_id: str, option_name: str, deprecation_info: dict):
        """
        :param model_id: 'shared' or 'instance' Used for the function name
        :param option_name: The option name
        :deprecation_info: Deprecation option information
        """
        self.deprecation_data[model_id][option_name] = deprecation_info

    def add_defaults(self, model_id: str, normalized_option_name: str, type_data: dict):
        """
        :param model_id: 'shared' or 'instance' Used for the function name
        :param normalized_option_name: Used to build the function name
        :type_data: dict containing all the relevant information to build the function
        """
        self.defaults_file_lines.extend(['', '', f'def {model_id}_{normalized_option_name}(field, value):'])

        default_value = self._get_default_value(type_data)
        if default_value is not NO_DEFAULT:
            self.defaults_file_needs_value_normalization = True
            self.defaults_file_lines.append(f'    return {default_value!r}')
        else:
            self.defaults_file_needs_dynamic_values = True
            self.defaults_file_lines.append('    return get_default_field_value(field, value)')

    @staticmethod
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
            if ModelInfo._example_looks_informative(example):
                return NO_DEFAULT
        elif isinstance(example, str):
            return NO_DEFAULT

        return example

    @staticmethod
    def _example_looks_informative(example):
        return '<' in example and '>' in example and example == example.upper()
