# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datamodel_code_generator.format import CodeFormatter

from datadog_checks.dev.tooling.configuration.consumers.model.model_info import ModelInfo


def build_model_file(
    parsed_document: str,
    model_id: str,
    section_name: str,
    model_info: ModelInfo,
    code_formatter: CodeFormatter,
):
    """
    :param parsed_document: OpenApi parsed document
    :param model_id: instance or shared
    :param section_name: init or instances
    :param model_info: Information to build the model file
    :param code_formatter:
    """
    # Whether or not there are options with default values
    options_with_defaults = len(model_info.defaults_file_lines) > 0
    model_file_lines = parsed_document.splitlines()
    _add_imports(model_file_lines, options_with_defaults, len(model_info.deprecation_data))

    if model_id in model_info.deprecation_data:
        model_file_lines += _define_deprecation_functions(model_id, section_name)

    model_file_lines += _define_validator_functions(model_id, model_info.validator_data, options_with_defaults)

    config_lines = []
    for i, line in enumerate(model_file_lines):
        if line.startswith('    model_config = ConfigDict('):
            config_lines.append(i)

    final_config_line = config_lines[-1]
    model_file_lines.insert(final_config_line + 1, '        validate_default=True,')

    model_file_lines.append('')
    model_file_contents = '\n'.join(model_file_lines)
    if any(len(line) > 120 for line in model_file_lines):
        model_file_contents = code_formatter.apply_black(model_file_contents)
    return model_file_contents


def _add_imports(model_file_lines, need_defaults, need_deprecations):
    import_lines = []

    for i, line in enumerate(model_file_lines):
        if line.startswith('from '):
            import_lines.append(i)

    # pydantic imports
    final_import_line = import_lines[-1]
    for index in reversed(import_lines):
        line = model_file_lines[index]
        if line.startswith('from pydantic '):
            model_file_lines[index] += ', field_validator, model_validator'
            break

    local_imports = ['validators']
    if need_defaults:
        local_imports.append('defaults')
    if need_deprecations:
        local_imports.append('deprecations')

    local_imports_part = ', '.join(sorted(local_imports))

    local_import_start_location = final_import_line + 1
    for line in reversed(
        (
            '',
            'from datadog_checks.base.utils.functions import identity',
            'from datadog_checks.base.utils.models import validation',
            '',
            f'from . import {local_imports_part}',
        )
    ):
        model_file_lines.insert(local_import_start_location, line)


def _define_deprecation_functions(model_id, section_name):
    model_file_lines = ['']
    model_file_lines.append("    @model_validator(mode='before')")
    model_file_lines.append('    def _handle_deprecations(cls, values, info):')
    model_file_lines.append("        fields = info.context['configured_fields']")
    model_file_lines.append(
        f'        validation.utils.handle_deprecations('
        f'{section_name!r}, deprecations.{model_id}(), fields, info.context)'
    )
    model_file_lines.append('        return values')
    return model_file_lines


def _define_validator_functions(model_id, validator_data, need_defaults):
    model_file_lines = ['']
    model_file_lines.append("    @model_validator(mode='before')")
    model_file_lines.append('    def _initial_validation(cls, values):')
    model_file_lines.append(
        f"        return validation.core.initialize_config("
        f"getattr(validators, 'initialize_{model_id}', identity)(values))"
    )

    if need_defaults:
        model_file_lines.append('')
        model_file_lines.append("    @field_validator('*', mode='before')")
        model_file_lines.append('    def _ensure_defaults(cls, value, info):')
        model_file_lines.append('        field = cls.model_fields[info.field_name]')
        model_file_lines.append('        field_name = field.alias or info.field_name')
        model_file_lines.append("        if field_name in info.context['configured_fields']:")
        model_file_lines.append('            return value')
        model_file_lines.append('')
        model_file_lines.append(f"        return getattr(defaults, f'{model_id}_{{info.field_name}}', lambda: value)()")

    model_file_lines.append('')
    model_file_lines.append("    @field_validator('*')")
    model_file_lines.append('    def _run_validations(cls, value, info):')
    model_file_lines.append('        field = cls.model_fields[info.field_name]')
    model_file_lines.append('        field_name = field.alias or info.field_name')
    model_file_lines.append("        if field_name not in info.context['configured_fields']:")
    model_file_lines.append('            return value')
    model_file_lines.append('')
    model_file_lines.append(
        f"        return getattr(validators, f'{model_id}_{{info.field_name}}', identity)(value, field=field)"
    )

    for option_name, import_paths in validator_data:
        for import_path in import_paths:
            validator_name = import_path.replace('.', '_')

            model_file_lines.append('')
            model_file_lines.append(f'    @field_validator({option_name!r})')
            model_file_lines.append(f'    def _run_{option_name}_{validator_name}(cls, value, info):')
            model_file_lines.append('        field = cls.model_fields[info.field_name]')
            model_file_lines.append('        field_name = field.alias or info.field_name')
            model_file_lines.append("        if field_name not in info.context['configured_fields']:")
            model_file_lines.append('            return value')
            model_file_lines.append('')
            model_file_lines.append(f'        return validation.{import_path}(value, field=field)')

    model_file_lines.append('')
    model_file_lines.append("    @field_validator('*', mode='after')")
    model_file_lines.append('    def _make_immutable(cls, value):')
    model_file_lines.append('        return validation.utils.make_immutable(value)')

    model_file_lines.append('')
    model_file_lines.append("    @model_validator(mode='after')")
    model_file_lines.append('    def _final_validation(cls, model):')
    model_file_lines.append(
        f"        return validation.core.check_model(getattr(validators, 'check_{model_id}', identity)(model))"
    )
    return model_file_lines
