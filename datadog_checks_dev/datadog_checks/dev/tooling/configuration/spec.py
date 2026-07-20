# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from string import Formatter
from typing import Any

from .constants import ALLOWED_FORMATS, OPENAPI_DATA_TYPES

DISCOVERY_FIELDS = {'strategies'}
DISCOVERY_TEMPLATE_CONTROL_FIELDS = {'template', 'overrides', 'enabled'}


def spec_validator(spec: dict, loader) -> None:
    if not isinstance(spec, dict):
        loader.errors.append(f'{loader.source}: Configuration specifications must be a mapping object')
        return

    release_version = spec.setdefault('version', loader.version)
    if not release_version:
        loader.errors.append(
            f'{loader.source}: Configuration specifications must contain a top-level `version` attribute'
        )
        return
    elif not isinstance(release_version, str):
        loader.errors.append(f'{loader.source}: The top-level `version` attribute must be a string')
        return

    if 'files' not in spec:
        loader.errors.append(
            f'{loader.source}: Configuration specifications must contain a top-level `files` attribute'
        )
        return

    files = spec['files']
    if not isinstance(files, list):
        loader.errors.append(f'{loader.source}: The top-level `files` attribute must be an array')
        return

    files_validator(files, loader)


def files_validator(files, loader) -> None:
    num_files = len(files)
    file_names_origin = {}
    example_file_names_origin = {}
    for file_index, config_file in enumerate(files, 1):
        if not isinstance(config_file, dict):
            loader.errors.append(f'{loader.source}, file #{file_index}: File attribute must be a mapping object')
            continue

        if 'name' not in config_file:
            loader.errors.append(
                '{}, file #{}: Every file must contain a `name` attribute representing the '
                'final destination the Agent loads'.format(loader.source, file_index)
            )
            continue

        file_name = config_file['name']
        if not isinstance(file_name, str):
            loader.errors.append(f'{loader.source}, file #{file_index}: Attribute `name` must be a string')
            continue

        if file_name in file_names_origin:
            loader.errors.append(
                '{}, file #{}: File name `{}` already used by file #{}'.format(
                    loader.source, file_index, file_name, file_names_origin[file_name]
                )
            )
        else:
            file_names_origin[file_name] = file_index

        if file_name == 'auto_conf.yaml' or file_name == 'conf.yaml.default':
            if 'example_name' in config_file and config_file['example_name'] != file_name:
                loader.errors.append(
                    '{}, file #{}: Example file name `{}` should be `{}`'.format(
                        loader.source, file_index, config_file['example_name'], file_name
                    )
                )

            example_file_name = config_file.setdefault('example_name', file_name)
        else:
            if num_files == 1:
                expected_name = f"{normalize_source_name(loader.source or 'conf')}.yaml"
                if file_name != expected_name:
                    loader.errors.append(
                        '{}, file #{}: File name `{}` should be `{}`'.format(
                            loader.source, file_index, file_name, expected_name
                        )
                    )

            example_file_name = config_file.setdefault('example_name', 'conf.yaml.example')

        if not isinstance(example_file_name, str):
            loader.errors.append(f'{loader.source}, file #{file_index}: Attribute `example_name` must be a string')

        if example_file_name in example_file_names_origin:
            loader.errors.append(
                '{}, file #{}: Example file name `{}` already used by file #{}'.format(
                    loader.source, file_index, example_file_name, example_file_names_origin[example_file_name]
                )
            )
        else:
            example_file_names_origin[example_file_name] = file_index

        if 'options' not in config_file:
            loader.errors.append(f'{loader.source}, {file_name}: Every file must contain an `options` attribute')
            continue

        options = config_file['options']
        if not isinstance(options, list):
            loader.errors.append(f'{loader.source}, {file_name}: The `options` attribute must be an array')
            continue

        options_validator(options, loader, file_name)

        if 'discovery' in config_file:
            handle_discovery(config_file, loader, file_name)


def expand_template_items(
    items: list, loader, file_name: str, section: str, propagate_hidden: bool = False
) -> set[int]:
    """Expand every template: item in items in-place.

    Overrides are shared across the whole list: ``apply_overrides`` pops each
    override as it is applied, so an override that cannot resolve against the
    current item is retried against later items, including nested templates that
    are spliced into the list as they expand (e.g. ``extra_metrics.value.*``).

    When ``propagate_hidden`` is set, a template wrapper's ``hidden`` value is
    carried forward (via ``setdefault``, so an item's own value wins) to every
    following item until the next template wrapper. Plain items do not start or
    reset propagation. This is the historical option-template behaviour that
    specs such as the Windows perf-counter checks and haproxy rely on to hide a
    block of legacy options; it is left off for discovery strategies, which have
    no ``hidden`` concept.

    Returns the set of 0-based indices that failed to resolve.
    """
    overrides: dict = {}
    override_errors: list = []
    failed: set[int] = set()
    pending_hidden = False
    i = 0
    while i < len(items):
        item = items[i]
        if not isinstance(item, dict) or 'template' not in item:
            if propagate_hidden and isinstance(item, dict):
                item.setdefault('hidden', pending_hidden)
            i += 1
            continue

        resolved = False

        while 'template' in item:
            if propagate_hidden:
                pending_hidden = item.get('hidden', False)
            overrides.update(item.pop('overrides', {}))
            try:
                tmpl = loader.templates.load(item.pop('template'))
            except Exception as e:
                loader.errors.append(f'{loader.source}, {file_name}, {section} #{i + 1}: {e}')
                break
            else:
                if 'name' in item:
                    tmpl['name'] = item['name']

            errors = loader.templates.apply_overrides(tmpl, overrides)
            if errors:
                override_errors.append((i, errors))

            if isinstance(tmpl, dict):
                tmpl.update(item)
                item = tmpl
                items[i] = tmpl
            elif isinstance(tmpl, list):
                if tmpl:
                    for k, tmpl_item in enumerate(tmpl):
                        items.insert(i + 1 + k, tmpl_item)
                    items.pop(i)
                    item = tmpl[0]
                    if not isinstance(item, dict):
                        loader.errors.append(
                            f'{loader.source}, {file_name}, {section} #{i + 1}: Template item must be a mapping object'
                        )
                        break
                else:
                    loader.errors.append(
                        f'{loader.source}, {file_name}, {section} #{i + 1}: Template refers to an empty array'
                    )
                    break
            else:
                loader.errors.append(
                    f'{loader.source}, {file_name}, {section} #{i + 1}: '
                    'Template does not refer to a mapping object nor array'
                )
                break
        else:
            resolved = True

        if resolved and propagate_hidden and isinstance(item, dict):
            item.setdefault('hidden', pending_hidden)

        if not resolved:
            failed.add(i)

        i += 1

    # Only overrides still present were never applied to any item; report those.
    if overrides and override_errors:
        for idx, errors in override_errors:
            error_message = '\n'.join(errors)
            loader.errors.append(f'{loader.source}, {file_name}, {section} #{idx + 1}: {error_message}')

    return failed


def _get_instance_option_names(options: list) -> frozenset[str]:
    """Return all option names from the instances section of a resolved options list.

    When `multiple_instances_defined` is set, each item under `instances` is a named
    group of options (one per instance mode) rather than a leaf field, so those groups
    must be flattened to collect the actual field names.
    """
    for section in options:
        if isinstance(section, dict) and section.get('name') == 'instances':
            section_opts = section.get('options', [])
            if isinstance(section_opts, list):
                return _flatten_option_names(section_opts)
    return frozenset()


def _flatten_option_names(options: list) -> frozenset[str]:
    names = set()
    for opt in options:
        if not isinstance(opt, dict):
            continue
        if isinstance(opt.get('options'), list):
            names.update(_flatten_option_names(opt['options']))
        elif 'name' in opt:
            names.add(opt['name'])
    return frozenset(names)


def _validate_strategy_input(stanza: dict, name: str, input_def: Any, loader: Any, location: str) -> None:
    """Validate a single declared strategy input against the resolved stanza."""
    if name not in stanza:
        if input_def.required:
            loader.errors.append(f'{location}: Attribute `{name}` is required')
        return

    value = stanza[name]
    if input_def.type == 'array[int]':
        if not isinstance(value, list) or not all(isinstance(v, int) and not isinstance(v, bool) for v in value):
            loader.errors.append(f'{location}: Attribute `{name}` must be an array of integers')
    elif input_def.type == 'integer':
        if not isinstance(value, int) or isinstance(value, bool):
            loader.errors.append(f'{location}: Attribute `{name}` must be an integer')
    elif input_def.type == 'string':
        if not isinstance(value, str):
            loader.errors.append(f'{location}: Attribute `{name}` must be a string')
    elif input_def.type == 'boolean':
        if not isinstance(value, bool):
            loader.errors.append(f'{location}: Attribute `{name}` must be true or false')


def discovery_validator(discovery: Any, options: list, loader: Any, file_name: str) -> None:
    import datadog_checks.dev.tooling.configuration.discovery.core_strategies  # noqa: F401
    from datadog_checks.dev.tooling.configuration.discovery.registry import (
        PORT_FIELDS,
        REGISTRY,
        SERVICE_FIELDS,
        Input,
    )

    location = f'{loader.source}, {file_name}, discovery'
    if not isinstance(discovery, dict):
        loader.errors.append(f'{location}: Attribute `discovery` must be a mapping object')
        return

    invalid_fields = set(discovery) - DISCOVERY_FIELDS
    if invalid_fields:
        fields = ', '.join(sorted(invalid_fields))
        loader.errors.append(f'{location}: Unknown field(s): {fields}')

    strategies = discovery.get('strategies')
    if not isinstance(strategies, list) or not strategies:
        loader.errors.append(f'{location}: Attribute `strategies` must be a non-empty array')
        return

    instance_option_names = _get_instance_option_names(options)

    for strategy_index, stanza in enumerate(strategies, 1):
        strategy_location = f'{location}, strategy #{strategy_index}'
        if not isinstance(stanza, dict):
            loader.errors.append(f'{strategy_location}: Strategy must be a mapping object')
            continue

        strategy_name = stanza.get('strategy')
        is_local = isinstance(strategy_name, str) and strategy_name.startswith('local:')

        if not is_local and strategy_name not in REGISTRY:
            loader.errors.append(f'{strategy_location}: Unsupported strategy `{strategy_name}`')
            continue

        reg = REGISTRY.get(strategy_name) if not is_local else None

        # Placeholders allowed in candidate templates: `service.*` is always
        # available, and each context key the strategy `provides` exposes a Port.
        placeholders: dict[str, frozenset[str]] = {'service': SERVICE_FIELDS}

        if reg is not None:
            allowed_fields = {'strategy', 'candidates', *reg.inputs}
            unknown = set(stanza) - allowed_fields
            if unknown:
                loader.errors.append(f'{strategy_location}: Unknown field(s): {", ".join(sorted(unknown))}')

            for input_name, input_def in reg.inputs.items():
                _validate_strategy_input(stanza, input_name, input_def, loader, strategy_location)

            for provided in reg.provides:
                placeholders[provided] = PORT_FIELDS
        else:
            # A local: strategy must declare its contract since dev cannot import it.
            local_provides = stanza.get('provides')
            if not isinstance(local_provides, list) or not all(isinstance(p, str) for p in local_provides):
                loader.errors.append(f'{strategy_location}: Attribute `provides` must be an array of strings')
            else:
                # Dev cannot know the field set of a local-provided context, so any
                # attribute is accepted on its placeholders.
                for provided in local_provides:
                    placeholders[provided] = None  # type: ignore[assignment]

            local_inputs = stanza.get('inputs')
            if not isinstance(local_inputs, dict):
                loader.errors.append(f'{strategy_location}: Attribute `inputs` must be a mapping object')
                local_inputs = {}
            elif not all(isinstance(k, str) and isinstance(v, str) for k, v in local_inputs.items()):
                loader.errors.append(f'{strategy_location}: Attribute `inputs` must map input names to type strings')
                local_inputs = {}

            allowed_fields = {'strategy', 'candidates', 'provides', 'inputs', *local_inputs}
            unknown = set(stanza) - allowed_fields
            if unknown:
                loader.errors.append(f'{strategy_location}: Unknown field(s): {", ".join(sorted(unknown))}')

            for input_name, input_type in local_inputs.items():
                _validate_strategy_input(stanza, input_name, Input(input_type), loader, strategy_location)

        candidates = stanza.get('candidates')
        if not isinstance(candidates, list) or not candidates:
            loader.errors.append(f'{strategy_location}: Attribute `candidates` must be a non-empty array')
            continue

        for candidate_index, candidate in enumerate(candidates, 1):
            candidate_location = f'{strategy_location}, candidate #{candidate_index}'
            if not isinstance(candidate, dict) or not candidate:
                loader.errors.append(f'{candidate_location}: Candidate must be a non-empty mapping object')
                continue

            for field_name, template in candidate.items():
                if not isinstance(field_name, str):
                    loader.errors.append(f'{candidate_location}: Candidate field names must be strings')
                    continue
                if instance_option_names and field_name not in instance_option_names:
                    loader.errors.append(f'{candidate_location}, {field_name}: Not a recognized instance option')

                validate_discovery_candidate_value(template, loader, candidate_location, field_name, placeholders)


def validate_discovery_candidate_value(
    value: Any, loader: Any, location: str, field_name: str, placeholders: dict[str, frozenset[str] | None]
) -> None:
    if isinstance(value, str):
        _validate_discovery_template(value, loader, location, field_name, placeholders)
    elif isinstance(value, dict):
        validate_discovery_candidate_mapping_keys(value, loader, location, field_name)


def validate_discovery_candidate_mapping_keys(
    value: dict[str, Any], loader: Any, location: str, field_name: str
) -> None:
    for key, item in value.items():
        if not isinstance(key, str):
            loader.errors.append(f'{location}, {field_name}: Candidate mapping keys must be strings')
            continue

        if isinstance(item, dict):
            validate_discovery_candidate_mapping_keys(item, loader, location, f'{field_name}.{key}')
        elif isinstance(item, list):
            for index, nested_item in enumerate(item, 1):
                if isinstance(nested_item, dict):
                    validate_discovery_candidate_mapping_keys(
                        nested_item, loader, location, f'{field_name}.{key}[{index}]'
                    )


def _validate_discovery_template(
    template: str, loader: Any, location: str, field_name: str, placeholders: dict[str, frozenset[str] | None]
) -> None:
    try:
        parsed_template = Formatter().parse(template)
    except ValueError as e:
        loader.errors.append(f'{location}, {field_name}: Invalid candidate template: {e}')
        return

    for _, placeholder, _, _ in parsed_template:
        if placeholder is None:
            continue

        root, separator, attr = placeholder.partition('.')
        if not separator or root not in placeholders:
            loader.errors.append(f'{location}, {field_name}: Unknown placeholder `{placeholder}`')
            continue

        # A `None` field-set means the root's attributes are unknown to dev (a
        # local: strategy's provided context), so any attribute is accepted.
        allowed_attrs = placeholders[root]
        if allowed_attrs is not None and attr not in allowed_attrs:
            loader.errors.append(f'{location}, {field_name}: Unknown placeholder `{placeholder}`')


def handle_discovery(config_file: dict, loader, file_name: str) -> None:
    """Resolve discovery templates, honour `enabled`, then validate.

    Runs after option-template resolution so the validator sees fully resolved
    data (D4). All discovery handling lives here, in one place at the tail of
    per-file processing.
    """
    discovery = config_file['discovery']
    if not isinstance(discovery, dict):
        loader.errors.append(f'{loader.source}, {file_name}, discovery: Attribute `discovery` must be a mapping object')
        return

    location = f'{loader.source}, {file_name}, discovery'

    # 1. Resolve a discovery-level template (if any), then expand strategy-item templates.
    if 'template' in discovery:
        overrides = discovery.pop('overrides', {})
        try:
            template = loader.templates.load(discovery.pop('template'))
        except Exception as e:
            loader.errors.append(f'{location}: {e}')
            return
        errors = loader.templates.apply_overrides(template, overrides)
        if errors:
            error_message = '\n'.join(errors)
            loader.errors.append(f'{location}: {error_message}')
        if not isinstance(template, dict):
            loader.errors.append(f'{location}: Template does not refer to a mapping object')
            return
        template.update(discovery)
        discovery = template
        config_file['discovery'] = discovery

    strategies = discovery.get('strategies')
    if isinstance(strategies, list):
        expand_template_items(strategies, loader, file_name, 'discovery, strategy')

    # 2. Honour `enabled: false` as a kill switch: drop the stanza so no
    #    discovery.py is generated.
    enabled = discovery.pop('enabled', True)
    if not enabled:
        del config_file['discovery']
        return

    # 3. Validate on the fully resolved stanza and resolved options.
    discovery_validator(discovery, config_file.get('options', []), loader, file_name)


def options_validator(options, loader, file_name, *sections):
    sections_display = ', '.join(sections)
    if sections_display:
        sections_display += ', '

    failed = expand_template_items(options, loader, file_name, f'{sections_display}option', propagate_hidden=True)

    option_names_origin = {}
    for option_index, option in enumerate(options, 1):
        if option_index - 1 in failed:
            continue

        if not isinstance(option, dict):
            loader.errors.append(
                '{}, {}, {}option #{}: Option attribute must be a mapping object'.format(
                    loader.source, file_name, sections_display, option_index
                )
            )
            continue

        if 'name' not in option:
            loader.errors.append(
                '{}, {}, {}option #{}: Every option must contain a `name` attribute'.format(
                    loader.source, file_name, sections_display, option_index
                )
            )
            continue

        option_name = option['name']
        if not isinstance(option_name, str):
            loader.errors.append(
                '{}, {}, {}option #{}: Attribute `name` must be a string'.format(
                    loader.source, file_name, sections_display, option_index
                )
            )

        # `hidden` is already set on every option by expand_template_items (propagate_hidden).
        if not isinstance(option['hidden'], bool):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `hidden` must be true or false'.format(
                    loader.source, file_name, sections_display, option_name
                )
            )

        if option_name in option_names_origin:
            if not option['hidden']:
                loader.errors.append(
                    '{}, {}, {}option #{}: Option name `{}` already used by option #{}'.format(
                        loader.source,
                        file_name,
                        sections_display,
                        option_index,
                        option_name,
                        option_names_origin[option_name],
                    )
                )
        else:
            option_names_origin[option_name] = option_index

        if 'description' not in option:
            loader.errors.append(
                '{}, {}, {}{}: Every option must contain a `description` attribute'.format(
                    loader.source, file_name, sections_display, option_name
                )
            )
            continue

        description = option['description']
        if not isinstance(description, str):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `description` must be a string'.format(
                    loader.source, file_name, sections_display, option_name
                )
            )

        option.setdefault('required', False)
        if not isinstance(option['required'], bool):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `required` must be true or false'.format(
                    loader.source, file_name, sections_display, option_name
                )
            )

        option.setdefault('display_priority', 0)
        if not isinstance(option['display_priority'], int):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `display_priority` must be an integer'.format(
                    loader.source, file_name, sections_display, option_name
                )
            )

        option.setdefault('deprecation', {})
        if not isinstance(option['deprecation'], dict):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `deprecation` must be a mapping object'.format(
                    loader.source, file_name, sections_display, option_name
                )
            )
        else:
            for key, info in option['deprecation'].items():
                if not isinstance(info, str):
                    loader.errors.append(
                        '{}, {}, {}{}: Key `{}` for attribute `deprecation` must be a string'.format(
                            loader.source, file_name, sections_display, option_name, key
                        )
                    )

        option.setdefault('metadata_tags', [])
        if not isinstance(option['metadata_tags'], list):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `metadata_tags` must be an array'.format(
                    loader.source, file_name, sections_display, option_name
                )
            )
        else:
            for metadata_tag in option['metadata_tags']:
                if not isinstance(metadata_tag, str):
                    loader.errors.append(
                        '{}, {}, {}{}: Attribute `metadata_tags` must only contain strings'.format(
                            loader.source, file_name, sections_display, option_name
                        )
                    )

        if 'formats' in option:
            formats_validator(option['formats'], loader, file_name, sections_display, option_name)

        if 'value' in option and 'options' in option:
            loader.errors.append(
                '{}, {}, {}{}: An option cannot contain both `value` and `options` attributes'.format(
                    loader.source, file_name, sections_display, option_name
                )
            )
            continue

        if 'value' in option:
            value = option['value']
            if not isinstance(value, dict):
                loader.errors.append(
                    '{}, {}, {}{}: Attribute `value` must be a mapping object'.format(
                        loader.source, file_name, sections_display, option_name
                    )
                )
                continue

            option.setdefault('secret', False)
            if not isinstance(option['secret'], bool):
                loader.errors.append(
                    '{}, {}, {}{}: Attribute `secret` must be true or false'.format(
                        loader.source, file_name, sections_display, option_name
                    )
                )

            value_validator(value, loader, file_name, sections_display, option_name, depth=0)
        elif 'options' in option:
            nested_options = option['options']
            if not isinstance(nested_options, list):
                loader.errors.append(
                    '{}, {}, {}{}: The `options` attribute must be an array'.format(
                        loader.source, file_name, sections_display, option_name
                    )
                )
                continue

            option.setdefault('multiple', False)
            if not isinstance(option['multiple'], bool):
                loader.errors.append(
                    '{}, {}, {}{}: Attribute `multiple` must be true or false'.format(
                        loader.source, file_name, sections_display, option_name
                    )
                )

            option.setdefault('multiple_instances_defined', False)
            if not isinstance(option['multiple_instances_defined'], bool):
                loader.errors.append(
                    '{}, {}, {}{}: Attribute `multiple` must be true or false'.format(
                        loader.source, file_name, sections_display, option_name
                    )
                )

            previous_sections = list(sections)
            previous_sections.append(option_name)
            options_validator(nested_options, loader, file_name, *previous_sections)


def formats_validator(formats, loader, file_name, sections_display, option_name, property_name=None):
    property_context = ''
    if property_name is not None:
        property_context = f' for property `{property_name}`'

    if not isinstance(formats, list):
        loader.errors.append(
            '{}, {}, {}{}: Attribute `formats`{} must be an array'.format(
                loader.source, file_name, sections_display, option_name, property_context
            )
        )
        return

    if not formats:
        loader.errors.append(
            '{}, {}, {}{}: Attribute `formats`{} must contain at least one entry'.format(
                loader.source, file_name, sections_display, option_name, property_context
            )
        )
        return

    if any(not isinstance(fmt, str) for fmt in formats):
        loader.errors.append(
            '{}, {}, {}{}: Attribute `formats`{} must only contain strings'.format(
                loader.source, file_name, sections_display, option_name, property_context
            )
        )
        return

    seen = set()
    duplicates = set()
    for fmt in formats:
        if fmt in seen:
            duplicates.add(fmt)
        else:
            seen.add(fmt)

    if duplicates:
        duplicate_display = ', '.join(sorted(duplicates))
        loader.errors.append(
            '{}, {}, {}{}: Attribute `formats`{} contains duplicate entries: {}'.format(
                loader.source, file_name, sections_display, option_name, property_context, duplicate_display
            )
        )

    invalid_formats = sorted(set(formats) - ALLOWED_FORMATS)
    if invalid_formats:
        valid_formats = ' | '.join(sorted(ALLOWED_FORMATS))
        invalid_display = ', '.join(invalid_formats)
        loader.errors.append(
            '{}, {}, {}{}: Attribute `formats`{} contains unknown value(s): {}, valid values are {}'.format(
                loader.source,
                file_name,
                sections_display,
                option_name,
                property_context,
                invalid_display,
                valid_formats,
            )
        )


def value_validator(value, loader, file_name, sections_display, option_name, depth=0):
    # Validate require_trusted_provider property if present
    if 'require_trusted_provider' in value and not isinstance(value['require_trusted_provider'], bool):
        loader.errors.append(
            '{}, {}, {}{}: Attribute `require_trusted_provider` must be true or false'.format(
                loader.source, file_name, sections_display, option_name
            )
        )

    if 'anyOf' in value:
        if 'type' in value:
            loader.errors.append(
                '{}, {}, {}{}: Values must contain either a `type` or `anyOf` attribute, not both'.format(
                    loader.source, file_name, sections_display, option_name
                )
            )
            return

        one_of = value['anyOf']
        if not isinstance(one_of, list):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `anyOf` must be an array'.format(
                    loader.source, file_name, sections_display, option_name
                )
            )
            return
        elif len(one_of) == 1:
            loader.errors.append(
                '{}, {}, {}{}: Attribute `anyOf` contains a single type, use the `type` attribute instead'.format(
                    loader.source, file_name, sections_display, option_name
                )
            )
            return

        for i, type_data in enumerate(one_of, 1):
            if not isinstance(type_data, dict):
                loader.errors.append(
                    '{}, {}, {}{}: Type #{} of attribute `anyOf` must be a mapping'.format(
                        loader.source, file_name, sections_display, option_name, i
                    )
                )
                return

            value_validator(type_data, loader, file_name, sections_display, option_name, depth=depth + 1)

        if not depth and value.get('example') is None:
            value['example'] = default_option_example(option_name)

        return
    elif 'type' not in value:
        loader.errors.append(
            '{}, {}, {}{}: Every value must contain a `type` attribute'.format(
                loader.source, file_name, sections_display, option_name
            )
        )
        return

    value_type = value['type']
    if not isinstance(value_type, str):
        loader.errors.append(
            '{}, {}, {}{}: Attribute `type` must be a string'.format(
                loader.source, file_name, sections_display, option_name
            )
        )
        return

    if value_type == 'string':
        if 'example' not in value:
            if not depth:
                value['example'] = default_option_example(option_name)
        elif not isinstance(value['example'], str):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `example` for `type` {} must be a string'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )

        if 'pattern' in value and not isinstance(value['pattern'], str):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `pattern` for `type` {} must be a string'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )
    elif value_type in ('integer', 'number'):
        if 'example' not in value:
            if not depth:
                value['example'] = default_option_example(option_name)
        elif not isinstance(value['example'], (int, float)):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `example` for `type` {} must be a number'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )

        minimum_valid = True
        maximum_valid = True

        if 'minimum' in value and not isinstance(value['minimum'], (int, float)):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `minimum` for `type` {} must be a number'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )
            minimum_valid = False

        if 'maximum' in value and not isinstance(value['maximum'], (int, float)):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `maximum` for `type` {} must be a number'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )
            maximum_valid = False

        if (
            'minimum' in value
            and 'maximum' in value
            and minimum_valid
            and maximum_valid
            and value['maximum'] <= value['minimum']
        ):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `maximum` for `type` {} must be greater than attribute `minimum`'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )
    elif value_type == 'boolean':
        if 'example' not in value:
            if not depth:
                loader.errors.append(
                    '{}, {}, {}{}: Every {} must contain a default `example` attribute'.format(
                        loader.source, file_name, sections_display, option_name, value_type
                    )
                )
        elif not isinstance(value['example'], bool):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `example` for `type` {} must be true or false'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )
    elif value_type == 'array':
        if 'example' not in value:
            if not depth:
                value['example'] = []
        elif not isinstance(value['example'], list):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `example` for `type` {} must be an array'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )

        if 'uniqueItems' in value and not isinstance(value['uniqueItems'], bool):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `uniqueItems` for `type` {} must be true or false'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )

        min_items_valid = True
        max_items_valid = True

        if 'minItems' in value and not isinstance(value['minItems'], int):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `minItems` for `type` {} must be an integer'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )
            min_items_valid = False

        if 'maxItems' in value and not isinstance(value['maxItems'], int):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `maxItems` for `type` {} must be an integer'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )
            max_items_valid = False

        if (
            'minItems' in value
            and 'maxItems' in value
            and min_items_valid
            and max_items_valid
            and value['maxItems'] <= value['minItems']
        ):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `maxItems` for `type` {} must be greater than attribute `minItems`'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )

        if 'items' not in value:
            loader.errors.append(
                '{}, {}, {}{}: Every {} must contain an `items` attribute'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )
            return

        items = value['items']
        if not isinstance(items, dict):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `items` for `type` {} must be a mapping object'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )
            return

        value_validator(items, loader, file_name, sections_display, option_name, depth=depth + 1)
    elif value_type == 'object':
        if 'example' not in value:
            if not depth:
                value['example'] = {}
        elif not isinstance(value['example'], dict):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `example` for `type` {} must be a mapping object'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )

        required = value.get('required')
        if 'required' in value:
            if not isinstance(required, list):
                loader.errors.append(
                    '{}, {}, {}{}: Attribute `required` for `type` {} must be an array'.format(
                        loader.source, file_name, sections_display, option_name, value_type
                    )
                )
                required = None
            elif not required:
                loader.errors.append(
                    '{}, {}, {}{}: Remove attribute `required` for `type` {} if no properties are required'.format(
                        loader.source, file_name, sections_display, option_name, value_type
                    )
                )
            elif len(required) - len(set(required)):
                loader.errors.append(
                    '{}, {}, {}{}: All entries in attribute `required` for `type` {} must be unique'.format(
                        loader.source, file_name, sections_display, option_name, value_type
                    )
                )

        properties = value.setdefault('properties', [])
        if not isinstance(properties, list):
            loader.errors.append(
                '{}, {}, {}{}: Attribute `properties` for `type` {} must be an array'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )
            return

        new_depth = depth + 1
        property_names = []
        for prop in properties:
            if not isinstance(prop, dict):
                loader.errors.append(
                    '{}, {}, {}{}: Every entry in `properties` for `type` {} must be a mapping object'.format(
                        loader.source, file_name, sections_display, option_name, value_type
                    )
                )

            if 'name' not in prop:
                loader.errors.append(
                    '{}, {}, {}{}: Every entry in `properties` for `type` {} must contain a `name` attribute'.format(
                        loader.source, file_name, sections_display, option_name, value_type
                    )
                )
                continue

            name = prop['name']
            if not isinstance(name, str):
                loader.errors.append(
                    '{}, {}, {}{}: Attribute `name` for `type` {} must be a string'.format(
                        loader.source, file_name, sections_display, option_name, value_type
                    )
                )
                continue

            property_names.append(name)

            if 'formats' in prop:
                formats_validator(prop['formats'], loader, file_name, sections_display, option_name, property_name=name)

            value_validator(prop, loader, file_name, sections_display, option_name, depth=new_depth)

        if len(property_names) - len(set(property_names)):
            loader.errors.append(
                '{}, {}, {}{}: All entries in attribute `properties` for `type` {} must have unique names'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )

        if required and set(required).difference(property_names):
            loader.errors.append(
                '{}, {}, {}{}: All entries in attribute `required` for `type` '
                '{} must be defined in the `properties` attribute'.format(
                    loader.source, file_name, sections_display, option_name, value_type
                )
            )

        if 'additionalProperties' in value:
            additional_properties = value['additionalProperties']
            if additional_properties is True:
                return
            elif not isinstance(additional_properties, dict):
                loader.errors.append(
                    '{}, {}, {}{}: Attribute `additionalProperties` for `type` {} must be a mapping or set '
                    'to `true`'.format(loader.source, file_name, sections_display, option_name, value_type)
                )
                return

            value_validator(additional_properties, loader, file_name, sections_display, option_name, depth=new_depth)
    else:
        loader.errors.append(
            '{}, {}, {}{}: Unknown type `{}`, valid types are {}'.format(
                loader.source,
                file_name,
                sections_display,
                option_name,
                value_type,
                ' | '.join(sorted(OPENAPI_DATA_TYPES)),
            )
        )


def default_option_example(option_name):
    return f'<{option_name.upper()}>'


def normalize_source_name(source_name):
    return source_name.lower().replace(' ', '_')
