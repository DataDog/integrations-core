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
    _fix_types(model_file_lines)

    if model_id in model_info.deprecation_data:
        model_file_lines += _define_deprecation_functions(model_id, section_name)

    model_file_lines += _define_validator_functions(model_id, model_info.validator_data, options_with_defaults)

    config_lines = []
    for i, line in enumerate(model_file_lines):
        if line.startswith('    model_config = ConfigDict('):
            config_lines.append(i)

    extra_config_lines = ['        arbitrary_types_allowed=True,']
    for i, line_number in enumerate(config_lines):
        index = line_number + (len(extra_config_lines) * i) + 1
        for line in extra_config_lines:
            model_file_lines.insert(index, line)

        if i == len(config_lines) - 1:
            model_file_lines.insert(index, '        validate_default=True,')

    model_file_lines.append('')
    model_file_contents = '\n'.join(model_file_lines)
    if any(len(line) > 120 for line in model_file_lines):
        model_file_contents = code_formatter.apply_black(model_file_contents)
    return model_file_contents


def _add_imports(model_file_lines, need_defaults, need_deprecations):
    import_lines = []
    mapping_found = False
    typing_location = -1

    for i, line in enumerate(model_file_lines):
        if line.startswith('from '):
            import_lines.append(i)
            if line.startswith('from typing '):
                typing_location = i
        elif 'dict[' in line:
            mapping_found = True

    # pydantic imports
    final_import_line = import_lines[-1]
    for index in reversed(import_lines):
        line = model_file_lines[index]
        if line.startswith('from pydantic '):
            model_file_lines[index] += ', field_validator, model_validator'
            break

    if mapping_found:
        if typing_location == -1:
            insertion_index = import_lines[0] + 1
            model_file_lines.insert(insertion_index, 'from types import MappingProxyType')
            model_file_lines.insert(insertion_index, '')
            final_import_line += 2
        else:
            model_file_lines.insert(typing_location, 'from types import MappingProxyType')
            final_import_line += 1

    local_imports = ['validators']
    if need_defaults:
        local_imports.append('defaults')
    if need_deprecations:
        local_imports.append('deprecations')

    local_import_start_location = final_import_line + 1
    for line in reversed(
        (
            '',
            'from datadog_checks.base.utils.functions import identity',
            'from datadog_checks.base.utils.models import validation',
            '',
            f'from . import {", ".join(sorted(local_imports))}',
        )
    ):
        model_file_lines.insert(local_import_start_location, line)


def _fix_types(model_file_lines):
    for i, line in enumerate(model_file_lines):
        line = model_file_lines[i] = line.replace('dict[', 'MappingProxyType[')
        if 'list[' not in line:
            continue

        buffer = bytearray()
        containers = []

        for char in line:
            if char == '[':
                if buffer[-4:] == b'list':
                    containers.append(True)
                    buffer[-4:] = b'tuple'
                else:
                    containers.append(False)
            elif char == ']' and containers.pop():
                buffer.extend(b', ...')

            buffer.append(ord(char))

        model_file_lines[i] = buffer.decode('utf-8')


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

    model_file_lines.append('')
    model_file_lines.append("    @field_validator('*', mode='before')")
    model_file_lines.append('    def _validate(cls, value, info):')
    model_file_lines.append('        field = cls.model_fields[info.field_name]')
    model_file_lines.append('        field_name = field.alias or info.field_name')
    model_file_lines.append("        if field_name in info.context['configured_fields']:")
    model_file_lines.append(
        f"            value = getattr(validators, f'{model_id}_{{info.field_name}}', identity)(value, field=field)"
    )

    for option_name, import_paths in sorted(validator_data):
        model_file_lines.append('')
        model_file_lines.append(f'            if info.field_name == {option_name!r}:')
        for import_path in import_paths:
            model_file_lines.append(f'                value = validation.{import_path}(value, field=field)')

    if need_defaults:
        model_file_lines.append('        else:')
        model_file_lines.append(
            f"            value = getattr(defaults, f'{model_id}_{{info.field_name}}', lambda: value)()"
        )

    model_file_lines.append('')
    model_file_lines.append('        return validation.utils.make_immutable(value)')

    model_file_lines.append('')
    model_file_lines.append("    @model_validator(mode='after')")
    model_file_lines.append('    def _final_validation(cls, model):')
    model_file_lines.append(
        f"        return validation.core.check_model(getattr(validators, 'check_{model_id}', identity)(model))"
    )
    return model_file_lines
