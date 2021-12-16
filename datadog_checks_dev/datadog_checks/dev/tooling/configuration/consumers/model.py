# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict
from typing import Dict, List, Tuple

import yaml
from datamodel_code_generator.format import CodeFormatter, PythonVersion
from datamodel_code_generator.parser import LiteralType
from datamodel_code_generator.parser.openapi import OpenAPIParser

from datadog_checks.dev.tooling.configuration.consumers.model_file import build_model_file
from datadog_checks.dev.tooling.configuration.consumers.openapi_document import build_openapi_document

PYTHON_VERSION = PythonVersion.PY_38


class ModelConsumer:
    def __init__(self, spec: dict, code_formatter: CodeFormatter = None):
        self.spec = spec
        self.code_formatter = code_formatter or self.create_code_formatter()

    def render(self) -> Dict[str, Dict[str, str]]:
        """
        Returns a dictionary containing for each spec file the list of rendered models
        """
        # { spec_file_name: {model_file_name: model_file_contents }
        rendered_files = {}

        for spec_file in self.spec['files']:
            # (<file name>, (<contents>, <errors>))
            model_files: Dict[str, Tuple[str, List[str]]] = {}
            # Contains pairs of model_id and schema_name. eg ('instance', 'InstanceConfig')
            model_data: List[Tuple[str, str]] = []
            # Contains function definitions as text for options that are optional so they have a default value
            defaults_file_lines: List[str] = []

            defaults_file_needs_dynamic_values = False
            defaults_file_needs_value_normalization = False
            deprecation_data = defaultdict(dict)

            # Sections are init_config and instances
            for section in sorted(spec_file['options'], key=lambda s: s['name']):
                (
                    section_model_files,
                    section_default_lines,
                    section_defaults_file_needs_value_normalization,
                    section_defaults_file_needs_dynamic_values,
                    section_deprecation_data,
                ) = self._process_section(section, model_data)
                model_files.update(section_model_files)
                defaults_file_lines.extend(section_default_lines)
                defaults_file_needs_value_normalization += section_defaults_file_needs_value_normalization
                defaults_file_needs_dynamic_values += section_defaults_file_needs_dynamic_values
                deprecation_data.update(section_deprecation_data)

            # Logs-only integrations
            if not model_files:
                continue

            if defaults_file_lines:
                defaults_file_contents = self._build_defaults_file(
                    defaults_file_needs_dynamic_values, defaults_file_needs_value_normalization, defaults_file_lines
                )
                model_files['defaults.py'] = (defaults_file_contents, [])

            if deprecation_data:
                deprecations_file_contents = self._build_deprecation_file(deprecation_data)
                model_files['deprecations.py'] = (deprecations_file_contents, [])

            package_root_lines = ModelConsumer._build_package_root(model_data)
            model_files['__init__.py'] = ('\n'.join(package_root_lines), [])

            # Custom
            model_files['validators.py'] = ('', [])

            rendered_files[spec_file['name']] = {file_name: model_files[file_name] for file_name in sorted(model_files)}

        return rendered_files

    def _process_section(self, section, model_data) -> (List[str], Dict[str, str], bool, bool, Dict[str, dict]):
        # Values to return
        section_default_lines = []
        model_files = {}
        section_defaults_file_needs_value_normalization = False
        section_defaults_file_needs_dynamic_values = False
        section_deprecation_data = defaultdict(dict)

        errors: List[str] = []
        section_name = section['name']
        if section_name == 'init_config':
            model_id = 'shared'
            model_file_name = f'{model_id}.py'
            schema_name = 'SharedConfig'
        elif section_name == 'instances':
            model_id = 'instance'
            model_file_name = f'{model_id}.py'
            schema_name = 'InstanceConfig'
            if section['multiple_instances_defined']:
                section = self._merge_instances(section, errors)
        # Skip anything checks don't use directly
        else:
            return (
                model_files,
                section_default_lines,
                section_defaults_file_needs_value_normalization,
                section_defaults_file_needs_dynamic_values,
                section_deprecation_data,
            )

        model_data.append((model_id, schema_name))
        (
            section_openapi_document,
            section_defaults_file_needs_value_normalization,
            section_defaults_file_needs_dynamic_values,
            section_default_lines,
            section_validator_data,
            section_deprecation_data,
        ) = build_openapi_document(section, model_id, schema_name, errors)

        try:
            section_parser = OpenAPIParser(
                yaml.safe_dump(section_openapi_document),
                target_python_version=PythonVersion.PY_38,
                enum_field_as_literal=LiteralType.All,
                encoding='utf-8',
                use_generic_container_types=True,
                enable_faux_immutability=True,
                # TODO: uncomment when the Agent upgrades Python to 3.9
                # use_standard_collections=True,
                strip_default_none=True,
                # https://github.com/koxudaxi/datamodel-code-generator/pull/173
                field_constraints=True,
            )
            parsed_section = section_parser.parse()
        except Exception as e:
            errors.append(f'Error parsing the OpenAPI schema `{schema_name}`: {e}')
            model_files[model_file_name] = ('', errors)
            return (
                model_files,
                section_default_lines,
                section_defaults_file_needs_value_normalization,
                section_defaults_file_needs_dynamic_values,
                section_deprecation_data,
            )

        options_with_defaults = len(section_default_lines) > 0
        model_file_contents = build_model_file(
            parsed_section,
            options_with_defaults,
            section_deprecation_data,
            model_id,
            section_name,
            section_validator_data,
            self.code_formatter,
        )
        # instance.py or shared.py
        model_files[model_file_name] = (model_file_contents, errors)
        return (
            model_files,
            section_default_lines,
            section_defaults_file_needs_value_normalization,
            section_defaults_file_needs_dynamic_values,
            section_deprecation_data,
        )

    def _merge_instances(self, section, errors):
        new_section = {
            'name': section['name'],
            'options': [],
        }
        # If one of these option is different for 2 options with the same name, an error is raised
        required_consistent_options = ['required', 'deprecation', 'metadata_tags']
        # Cache the option index to ease option checking before merging
        options_name_idx = {}

        for instance in section['options']:
            for opt in instance['options']:
                if options_name_idx.get(opt['name']) is not None:
                    cached_opt = new_section['options'][options_name_idx[opt['name']]]

                    for opt_name in required_consistent_options:
                        if cached_opt[opt_name] != opt[opt_name]:
                            errors.append(
                                f'Options {cached_opt} and {opt} have a different value for attribute `{opt_name}`'
                            )
                    if cached_opt['value']['type'] != opt['value']['type']:
                        errors.append(f'Options {cached_opt} and {opt} have a different value for attribute `type`')

                else:
                    new_section['options'].append(opt)
                    options_name_idx[opt['name']] = len(new_section['options']) - 1

        return new_section

    @staticmethod
    def create_code_formatter():
        return CodeFormatter(PYTHON_VERSION)

    def _build_deprecation_file(self, deprecation_data):
        file_needs_formatting = False
        deprecations_file_lines = []
        for model_id, deprecations in deprecation_data.items():
            deprecations_file_lines.append('')
            deprecations_file_lines.append('')
            deprecations_file_lines.append(f'def {model_id}():')
            deprecations_file_lines.append(f'    return {deprecations!r}')
            if len(deprecations_file_lines[-1]) > 120:
                file_needs_formatting = True

        deprecations_file_lines.append('')
        deprecations_file_contents = '\n'.join(deprecations_file_lines)
        if file_needs_formatting:
            deprecations_file_contents = self.code_formatter.apply_black(deprecations_file_contents)
        return deprecations_file_contents

    @staticmethod
    def _build_package_root(model_data):
        model_data.sort()
        package_root_lines = []
        for model_id, schema_name in model_data:
            package_root_lines.append(f'from .{model_id} import {schema_name}')

        package_root_lines.append('')
        package_root_lines.append('')
        package_root_lines.append('class ConfigMixin:')
        for model_id, schema_name in model_data:
            package_root_lines.append(f'    _config_model_{model_id}: {schema_name}')
        for model_id, schema_name in model_data:
            property_name = 'config' if model_id == 'instance' else f'{model_id}_config'
            package_root_lines.append('')
            package_root_lines.append('    @property')
            package_root_lines.append(f'    def {property_name}(self) -> {schema_name}:')
            package_root_lines.append(f'        return self._config_model_{model_id}')

        package_root_lines.append('')
        return package_root_lines

    def _build_defaults_file(
        self, defaults_file_needs_dynamic_values, defaults_file_needs_value_normalization, defaults_file_lines
    ):
        if defaults_file_needs_dynamic_values:
            defaults_file_lines.insert(0, 'from datadog_checks.base.utils.models.fields import get_default_field_value')

        defaults_file_lines.append('')
        defaults_file_contents = '\n'.join(defaults_file_lines)
        if defaults_file_needs_value_normalization:
            defaults_file_contents = self.code_formatter.apply_black(defaults_file_contents)
        return defaults_file_contents
