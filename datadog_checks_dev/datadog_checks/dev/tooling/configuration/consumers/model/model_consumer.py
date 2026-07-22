# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import warnings
from pprint import pformat
from typing import Any, Dict, List, Tuple

import yaml
from datamodel_code_generator import DataModelType
from datamodel_code_generator.format import PythonVersion
from datamodel_code_generator.model import get_data_model_types
from datamodel_code_generator.parser import LiteralType
from datamodel_code_generator.parser.openapi import OpenAPIParser

from datadog_checks.dev.tooling.configuration.consumers.model.code_formatter import format_with_ruff
from datadog_checks.dev.tooling.configuration.consumers.model.model_file import build_model_file
from datadog_checks.dev.tooling.configuration.consumers.model.model_info import ModelInfo
from datadog_checks.dev.tooling.configuration.consumers.openapi_document import build_openapi_document

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

DISCOVERY_STRATEGIES_DOCUMENTATION = '''# Here you can define custom (local:) discovery strategies for this integration.
#
# Decorate a generator with @discovery_strategy (imported from
# datadog_checks.base.utils.discovery) and reference it from the spec discovery
# stanza as `strategy: local:<function_name>`. The function receives the
# discovered Service plus the inputs declared in the spec and yields one context
# (ctx) mapping per candidate, exposing the keys listed in `provides`.
#
# from datadog_checks.base.utils.discovery import discovery_strategy
#
# @discovery_strategy(provides=('svc',))
# def from_some_config(service, config_path):
#     ...
#     yield {'svc': ...}
'''

DISCOVERY_OVERRIDES_DOCUMENTATION = '''# Override the generated discovery candidates() for this integration.
#
# Define a candidates(service, default) function to wrap or replace the generated
# candidate generation. `default` is the generated generator; call it to reuse
# the spec-driven candidates, or ignore it to replace them entirely.
#
# def candidates(service, default):
#     yield from default(service)
'''


class ModelConsumer:
    def __init__(self, spec: dict):
        self.spec = spec

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
                ) = self._process_section(section, spec_file['name'])
                package_info.extend(section_package_info)
                model_files.update(section_model_files)
                model_info.update(section_model_info)

            # Logs-only integrations
            if not model_files:
                continue

            model_files.update(self._build_model_files(model_info, package_info))
            if 'discovery' in spec_file:
                pkg_name = spec_file['name'].removesuffix('.yaml')
                has_shared = any(s['name'] == 'init_config' for s in spec_file.get('options', []))
                model_files['discovery.py'] = (
                    self._build_discovery_file(spec_file['discovery'], pkg_name, has_shared=has_shared),
                    [],
                )
                # Custom (written once, preserved across regens; see CUSTOM_FILES)
                model_files['discovery_strategies.py'] = (DISCOVERY_STRATEGIES_DOCUMENTATION, [])
                model_files['discovery_overrides.py'] = (DISCOVERY_OVERRIDES_DOCUMENTATION, [])
            rendered_files[spec_file['name']] = {file_name: model_files[file_name] for file_name in sorted(model_files)}

        return rendered_files

    def _process_section(self, section, spec_file_name: str = '') -> (List[Tuple[str, str]], dict, ModelInfo):
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
            # auto_conf.yaml files may define instances as a leaf (no sub-options) to
            # emit `instances: []` without providing a model schema.
            if 'options' not in section and spec_file_name == 'auto_conf.yaml':
                return (package_info, model_files, model_info)
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
            deprecations_file_contents = format_with_ruff(deprecations_file_contents)
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
            defaults_file_contents = format_with_ruff(defaults_file_contents)
        return defaults_file_contents

    def _build_discovery_file(self, discovery: dict[str, Any], pkg_name: str, *, has_shared: bool = True) -> str:
        import datadog_checks.dev.tooling.configuration.discovery.core_strategies  # noqa: F401
        from datadog_checks.dev.tooling.configuration.discovery.registry import REGISTRY

        strategies = discovery.get('strategies', [])

        # `Service` is always needed for the signature; each strategy contributes
        # its own runtime imports (`candidate_ports` for core strategies, the
        # discovery_strategies function for local: ones) plus the section models.
        import_lines = [
            'from datadog_checks.base.utils.discovery import Service',
            f'from datadog_checks.{pkg_name}.config_models import discovery_overrides',
            f'from datadog_checks.{pkg_name}.config_models.instance import InstanceConfig',
        ]
        if has_shared:
            import_lines.append(f'from datadog_checks.{pkg_name}.config_models.shared import SharedConfig')
        for stanza in strategies:
            strategy_name = stanza['strategy']
            if strategy_name.startswith('local:'):
                func = strategy_name.split(':', 1)[1]
                import_lines.append(f'from datadog_checks.{pkg_name}.config_models.discovery_strategies import {func}')
            else:
                import_lines.extend(REGISTRY[strategy_name].runtime_imports)

        if has_shared:
            shared_line = [
                "    shared = SharedConfig.model_validate({}, context={'configured_fields': frozenset()}).model_dump(",
                "        by_alias=True, mode='json', exclude_none=True",
                "    )",
            ]
        else:
            shared_line = ['    shared = {}']

        lines = [
            'from __future__ import annotations',
            '',
            'from collections.abc import Iterator',
            'from typing import Any',
            '',
            *self._merge_import_lines(import_lines),
            '',
            '',
            'def _generated_candidates(service: Service) -> Iterator[dict[str, Any]]:',
            *shared_line,
        ]

        for index, stanza in enumerate(strategies):
            strategy_name = stanza['strategy']
            lines.append(f'    # discovery[{index}]: {strategy_name}')
            lines.extend(self._emit_strategy_loop(stanza, strategy_name))
            for candidate in stanza.get('candidates', []):
                lines.extend(self._emit_candidate_body(candidate))

        lines.extend(
            [
                '',
                '',
                'def candidates(service: Service) -> Iterator[dict[str, Any]]:',
                "    override = getattr(discovery_overrides, 'candidates', None)",
                '    if override is None:',
                '        yield from _generated_candidates(service)',
                '    else:',
                '        yield from override(service, default=_generated_candidates)',
                '',
            ]
        )
        return format_with_ruff('\n'.join(lines))

    @staticmethod
    def _merge_import_lines(import_lines: list[str]) -> list[str]:
        """Group `from M import N` lines by module into canonical isort order.

        Mirrors ruff/isort so the generated file is stable under `ddev test -fs`:
        modules sorted alphabetically, names within a module ordered by type
        (classes/constants before lowercase functions), deduped.
        """
        modules: dict[str, set[str]] = {}
        for line in import_lines:
            module, _, names = line.removeprefix('from ').partition(' import ')
            modules.setdefault(module, set()).update(name.strip() for name in names.split(','))

        merged = []
        for module in sorted(modules):
            names = sorted(modules[module], key=lambda name: (name[:1].islower(), name))
            merged.append(f'from {module} import {", ".join(names)}')
        return merged

    @staticmethod
    def _emit_strategy_loop(stanza: dict[str, Any], strategy_name: str) -> list[str]:
        """Emit the per-candidate loop header that binds `ctx`."""
        from datadog_checks.dev.tooling.configuration.discovery.registry import REGISTRY

        if strategy_name.startswith('local:'):
            func = strategy_name.split(':', 1)[1]
            reserved = {'strategy', 'candidates', 'provides', 'inputs'}
            kwargs = ', '.join(f'{key}={value!r}' for key, value in stanza.items() if key not in reserved)
            call = f'{func}(service, {kwargs})' if kwargs else f'{func}(service)'
            return [f'    for ctx in {call}:']

        return REGISTRY[strategy_name].emit_context(stanza)

    @staticmethod
    def _emit_candidate_body(candidate: dict[str, Any]) -> list[str]:
        """Emit the model-backed candidate construction for one candidate mapping."""
        lines = ['        instance_data = {']
        for field_name, value in candidate.items():
            rendered = ModelConsumer._render_candidate_value(value)
            lines.append(f'            {field_name!r}: {rendered},')
        lines.append('        }')
        lines.append('        instance = InstanceConfig.model_validate(')
        lines.append("            instance_data, context={'configured_fields': frozenset(instance_data)}")
        lines.append("        ).model_dump(by_alias=True, mode='json', exclude_none=True)")
        lines.append("        yield {'init_config': shared, 'instances': [instance]}")
        return lines

    @staticmethod
    def _render_candidate_value(value: Any) -> str:
        """Render a discovery candidate value as a Python expression."""
        if isinstance(value, str):
            if '{' in value:
                return f'{value!r}.format(service=service, **ctx)'

            return repr(value)

        return pformat(value, width=120, sort_dicts=False)
