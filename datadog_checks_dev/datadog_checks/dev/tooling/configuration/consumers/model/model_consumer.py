# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import yaml
from datamodel_code_generator import DataModelType
from datamodel_code_generator.format import CodeFormatter, PythonVersion
from datamodel_code_generator.model import get_data_model_types
from datamodel_code_generator.parser import LiteralType
from datamodel_code_generator.parser.openapi import OpenAPIParser

from datadog_checks.dev.tooling.configuration.consumers.model.model_file import build_model_file
from datadog_checks.dev.tooling.configuration.consumers.model.model_info import ModelInfo
from datadog_checks.dev.tooling.configuration.consumers.openapi_document import build_openapi_document
from datadog_checks.dev.tooling.constants import get_root

PYTHON_VERSION = PythonVersion.PY_39

VALIDATORS_DOCUMENTATION = '''# Here you can include additional config validators or transformers
#
# def initialize_instance(values, **kwargs):
#     if 'my_option' not in values and 'my_legacy_option' in values:
#         values['my_option'] = values['my_legacy_option']
#     if values.get('my_number') > 10:
#         raise ValueError('my_number max value is 10, got %s' % str(values.get('my_number')))
#
#     return values
'''


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
            package_info: List[Tuple[str, str]] = []
            model_info = ModelInfo()

            # Sections are init_config and instances
            for section in sorted(spec_file['options'], key=lambda s: s['name']):
                (
                    section_package_info,
                    section_model_files,
                    section_model_info,
                ) = self._process_section(section)
                package_info.extend(section_package_info)
                model_files.update(section_model_files)
                model_info.update(section_model_info)

            # Logs-only integrations
            if not model_files:
                continue

            model_files.update(self._build_model_files(model_info, package_info))
            rendered_files[spec_file['name']] = {file_name: model_files[file_name] for file_name in sorted(model_files)}

        return rendered_files

    def _process_section(self, section) -> (List[Tuple[str, str]], dict, ModelInfo):
        # Values to return
        # [(model_id, schema_name)]
        package_info: List[Tuple[str, str]] = []
        # { model_file_name: (model_file_contents, errors) }
        model_files: Dict[str, Tuple[str, List[str]]] = {}
        model_info = ModelInfo()

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
                package_info,
                model_files,
                model_info,
            )

        package_info.append((model_id, schema_name))
        (section_openapi_document, model_info) = build_openapi_document(section, model_id, schema_name, errors)

        model_types = get_data_model_types(DataModelType.PydanticV2BaseModel, target_python_version=PYTHON_VERSION)
        try:
            section_parser = OpenAPIParser(
                yaml.safe_dump(section_openapi_document),
                data_model_type=model_types.data_model,
                data_model_root_type=model_types.root_model,
                data_model_field_type=model_types.field_model,
                data_type_manager_type=model_types.data_type_manager,
                dump_resolve_reference_action=model_types.dump_resolve_reference_action,
                enum_field_as_literal=LiteralType.All,
                encoding='utf-8',
                enable_faux_immutability=True,
                use_standard_collections=True,
                strip_default_none=True,
                # https://github.com/koxudaxi/datamodel-code-generator/pull/173
                field_constraints=True,
            )
            # https://github.com/pydantic/pydantic/issues/6422
            # https://github.com/pydantic/pydantic/issues/6467#issuecomment-1623680485
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                parsed_section = section_parser.parse()
        except Exception as e:
            errors.append(f'Error parsing the OpenAPI schema `{schema_name}`: {e}')
            model_files[model_file_name] = ('', errors)
            return (
                package_info,
                model_files,
                model_info,
            )

        model_file_contents = build_model_file(
            parsed_section,
            model_id,
            section_name,
            model_info,
            self.code_formatter,
        )
        # instance.py or shared.py
        model_files[model_file_name] = (model_file_contents, errors)
        return (
            package_info,
            model_files,
            model_info,
        )

    def _build_model_files(
        self, model_info: ModelInfo, package_info: List[Tuple[str, str]]
    ) -> Dict[str, Tuple[str, List]]:
        """Builds the model files others than instace.py and shared.py
        In particular it builds, if relevant:
            - defaults.py
            - deprecations.py
            - __init__.py
            - validators.py
        Returns a Dict[ file_name, Tuple[file_contents, List[errors])]
        """
        model_files = {}
        if model_info.defaults_file_lines:
            defaults_file_contents = self._build_defaults_file(model_info)
            model_files['defaults.py'] = (f'\n{defaults_file_contents}', [])

        if model_info.deprecation_data:
            deprecations_file_contents = self._build_deprecation_file(model_info.deprecation_data)
            model_files['deprecations.py'] = (deprecations_file_contents, [])

        package_root_lines = ModelConsumer._build_package_root(package_info)
        model_files['__init__.py'] = ('\n'.join(package_root_lines), [])

        # Custom
        model_files['validators.py'] = (VALIDATORS_DOCUMENTATION, [])
        return model_files

    def _merge_instances(self, section: dict, errors: List[str]) -> dict:
        """Builds a new, unified, section by merging multiple
        :param section: The section to unify
        :param errors: The list where to add errors
        """
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
        path = Path(get_root())
        return CodeFormatter(PYTHON_VERSION, settings_path=path if path.is_dir() else None)

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
    def _build_package_root(package_info):
        package_info.sort()
        package_root_lines = []
        for model_id, schema_name in package_info:
            package_root_lines.append(f'from .{model_id} import {schema_name}')

        package_root_lines.append('')
        package_root_lines.append('')
        package_root_lines.append('class ConfigMixin:')
        for model_id, schema_name in package_info:
            package_root_lines.append(f'    _config_model_{model_id}: {schema_name}')
        for model_id, schema_name in package_info:
            property_name = 'config' if model_id == 'instance' else f'{model_id}_config'
            package_root_lines.append('')
            package_root_lines.append('    @property')
            package_root_lines.append(f'    def {property_name}(self) -> {schema_name}:')
            package_root_lines.append(f'        return self._config_model_{model_id}')

        package_root_lines.append('')
        return package_root_lines

    def _build_defaults_file(self, model_info: ModelInfo):
        model_info.defaults_file_lines.append('')
        defaults_file_contents = '\n'.join(model_info.defaults_file_lines)
        if model_info.defaults_file_needs_value_normalization:
            defaults_file_contents = self.code_formatter.apply_black(defaults_file_contents)
        return defaults_file_contents
