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

    model_file_lines += _define_validator_functions(model_id, model_info.validator_data)

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
    model_file_lines[final_import_line] += ', root_validator, validator'

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
    model_file_lines.append('    @root_validator(pre=True)')
    model_file_lines.append('    def _handle_deprecations(cls, values):')
    model_file_lines.append(
        f'        validation.utils.handle_deprecations(' f'{section_name!r}, deprecations.{model_id}(), values)'
    )
    model_file_lines.append('        return values')
    return model_file_lines


def _define_validator_functions(model_id, validator_data):
    model_file_lines = ['']
    model_file_lines.append('    @root_validator(pre=True)')
    model_file_lines.append('    def _initial_validation(cls, values):')
    model_file_lines.append(
        f"        return validation.core.initialize_config("
        f"getattr(validators, 'initialize_{model_id}', identity)(values))"
    )

    model_file_lines.append('')
    model_file_lines.append("    @validator('*', pre=True, always=True)")
    model_file_lines.append('    def _ensure_defaults(cls, v, field):')
    model_file_lines.append('        if v is not None or field.required:')
    model_file_lines.append('            return v')
    model_file_lines.append('')
    model_file_lines.append(f"        return getattr(defaults, f'{model_id}_{{field.name}}')(field, v)")

    model_file_lines.append('')
    model_file_lines.append("    @validator('*')")
    model_file_lines.append('    def _run_validations(cls, v, field):')
    # TODO: remove conditional when there is a workaround:
    # https://github.com/samuelcolvin/pydantic/issues/2376
    model_file_lines.append('        if not v:')
    model_file_lines.append('            return v')
    model_file_lines.append('')
    model_file_lines.append(
        f"        return getattr(validators, f'{model_id}_{{field.name}}', identity)(v, field=field)"
    )

    for option_name, import_paths in validator_data:
        for import_path in import_paths:
            validator_name = import_path.replace('.', '_')

            model_file_lines.append('')
            model_file_lines.append(f'    @validator({option_name!r})')
            model_file_lines.append(f'    def _run_{option_name}_{validator_name}(cls, v, field):')
            # TODO: remove conditional when there is a workaround:
            # https://github.com/samuelcolvin/pydantic/issues/2376
            model_file_lines.append('        if not v:')
            model_file_lines.append('            return v')
            model_file_lines.append('')
            model_file_lines.append(f'        return validation.{import_path}(v, field=field)')

    model_file_lines.append('')
    model_file_lines.append('    @root_validator(pre=False)')
    model_file_lines.append('    def _final_validation(cls, values):')
    model_file_lines.append(
        f"        return validation.core.finalize_config("
        f"getattr(validators, 'finalize_{model_id}', identity)(values))"
    )
    return model_file_lines
