# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .constants import OPENAPI_DATA_TYPES
from .utils import default_option_example, normalize_source_name


def spec_validator(spec, loader):
    if not isinstance(spec, dict):
        loader.errors.append(f'{loader.source}: Configuration specifications must be a mapping object')
        return

    if 'name' not in spec:
        loader.errors.append(f'{loader.source}: Configuration specifications must contain a top-level `name` attribute')
        return

    name = spec['name']
    if not isinstance(name, str):
        loader.errors.append(f'{loader.source}: The top-level `name` attribute must be a string')
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


def files_validator(files, loader):
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

        if file_name == 'auto_conf.yaml':
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


def options_validator(options, loader, file_name, *sections):
    sections_display = ', '.join(sections)
    if sections_display:
        sections_display += ', '

    overrides = {}
    override_errors = []

    option_names_origin = {}
    hide_template = False
    for option_index, option in enumerate(options, 1):
        if not isinstance(option, dict):
            loader.errors.append(
                '{}, {}, {}option #{}: Option attribute must be a mapping object'.format(
                    loader.source, file_name, sections_display, option_index
                )
            )
            continue

        templates_resolved = False
        while 'template' in option:
            hide_template = option.get('hidden', False)

            overrides.update(option.pop('overrides', {}))
            try:
                template = loader.templates.load(option.pop('template'))
            except Exception as e:
                loader.errors.append(f'{loader.source}, {file_name}, {sections_display}option #{option_index}: {e}')
                break

            errors = loader.templates.apply_overrides(template, overrides)
            if errors:
                override_errors.append((option_index, errors))

            if isinstance(template, dict):
                template.update(option)
                option = template
                options[option_index - 1] = template
            elif isinstance(template, list):
                if template:
                    option = template[0]
                    for item_index, template_item in enumerate(template):
                        options.insert(option_index + item_index, template_item)

                    # Delete what's at the current index
                    options.pop(option_index - 1)

                    # Perform this check once again
                    if not isinstance(option, dict):
                        loader.errors.append(
                            '{}, {}, {}option #{}: Template option must be a mapping object'.format(
                                loader.source, file_name, sections_display, option_index
                            )
                        )
                        break
                else:
                    loader.errors.append(
                        '{}, {}, {}option #{}: Template refers to an empty array'.format(
                            loader.source, file_name, sections_display, option_index
                        )
                    )
                    break
            else:
                loader.errors.append(
                    '{}, {}, {}option #{}: Template does not refer to a mapping object nor array'.format(
                        loader.source, file_name, sections_display, option_index
                    )
                )
                break

        # Only set upon success or if there were no templates
        else:
            templates_resolved = True

        if not templates_resolved:
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

        option.setdefault('hidden', hide_template)
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

    # If there are unused overrides, add the associated error messages
    if overrides:
        for option_index, errors in override_errors:
            error_message = '\n'.join(errors)
            loader.errors.append(
                f'{loader.source}, {file_name}, {sections_display}option #{option_index}: {error_message}'
            )


def value_validator(value, loader, file_name, sections_display, option_name, depth=0):
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
