# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections import namedtuple

# Simple validation tuple, with some interesting caveats:
#
# `key` - name of value in the object
# `type` - must be a builtin object - e.g. int, str, list, dict.
# `required` - whether the key must be present
# `default` - if False, then key will be initialized via the `type`.  Note that for `bool` types,
#     this initializes to `False`.
# `children` - if this item can have sub-elements, and how to validate them.  Can be an explicit
#     list of other Validation objects, or the special `self` indicating recursive validation.
Validation = namedtuple('Validation', 'key, type, required, default, children', defaults=(str, True, None, None))


def _validate(obj, items, loader, MISSING, INVALID):
    for v in items:
        if v.required and v.key not in obj:
            loader.errors.append(MISSING.format(loader=loader, key=v.key, type=v.type))
            return

        if v.key in obj:
            if not isinstance(obj[v.key], v.type):
                loader.errors.append(INVALID.format(loader=loader, key=v.key, type=v.type))
        else:
            if v.default is not None:
                obj[v.key] = v.default
            else:
                # initialize as empty builtin type
                obj[v.key] = v.type()

        if v.children and obj[v.key]:
            # handle recursive elements which may be passed as strings
            if v.children == 'self':
                children = items
            else:
                children = v.children
            _validate(obj[v.key], children, loader, MISSING, INVALID)


def spec_validator(spec, loader):
    if not isinstance(spec, dict):
        loader.errors.append(f'{loader.source}: {loader.spec_type} specifications must be a mapping object')
        return

    MISSING = '{loader.source}: {loader.spec_type} specifications must include a top-level `{key}` attribute.'
    INVALID = '{loader.source}: The top-level `{key}` attribute must be a {type}'

    valid_options = [Validation(key='autodiscovery', type=bool, required=False)]
    validations = [
        Validation(key='name', type=str),
        Validation(key='version', type=str, required=False),
        Validation(key='options', type=dict, required=False, children=valid_options),
        Validation(key='files', type=list),
    ]

    _validate(spec, validations, loader, MISSING, INVALID)

    if loader.errors:
        return

    files_validator(spec['files'], loader)


def files_validator(files, loader):

    validations = [
        Validation(key='name'),
        Validation(key='render_name', type=str, required=False, default='README.md'),
        Validation(key='sections', type=list),  # validate section attributes separately rather than children
    ]

    file_names = {}
    render_names = {}

    for file_index, doc_file in enumerate(files, 1):
        MISSING = f'{loader.source}: {loader.spec_type} file #{file_index}: Must include a `{{key}}` attribute.'
        INVALID = f'{loader.source}: {loader.spec_type} file #{file_index}: Attribute `{{key}}` must be a {{type}}'

        if not isinstance(doc_file, dict):
            loader.errors.append(f'{loader.source}, file #{file_index}: File attribute must be a mapping object')
            continue

        _validate(doc_file, validations, loader, MISSING, INVALID)

        # Check for duplicate names
        file_name = doc_file['name']
        if file_name in file_names:
            loader.errors.append(
                '{}, file #{}: File name `{}` already used by file #{}'.format(
                    loader.source, file_index, file_name, file_names[file_name]
                )
            )
        else:
            file_names[file_name] = file_index

        render_name = doc_file['render_name']
        if render_name in render_names:
            loader.errors.append(
                '{}, file #{}: Doc file name `{}` already used by file #{}'.format(
                    loader.source, file_index, render_name, render_names[render_name]
                )
            )
        else:
            render_names[render_name] = file_index

        sections = doc_file['sections']
        section_validator(sections, loader, file_name)


def section_validator(sections, loader, file_name, *prev_sections):
    sections_display = ', '.join(prev_sections)
    if sections_display:
        sections_display += ', '

    validations = [
        Validation(key='name'),
        Validation(key='header_level', type=int),
        Validation(key='tab', type=str, required=False),
        Validation(key='description'),
        Validation(key='parameters', type=dict, required=False),
        Validation(key='prepend_text', type=str, required=False),
        Validation(key='append_text', type=str, required=False),
        Validation(key='processor', type=str, required=False),
        Validation(key='hidden', type=bool, required=False),
        Validation(key='sections', type=list, required=False, children='self'),
        Validation(key='overrides', type=list, required=False),
    ]

    overrides = {}
    override_errors = []

    section_names_origin = {}
    for section_index, section in enumerate(sections, 1):
        if not isinstance(section, dict):
            loader.errors.append(
                '{}, {}, {}section #{}: section attribute must be a mapping object'.format(
                    loader.source, file_name, sections_display, section_index
                )
            )
            continue

        # expand and override all templates within the section
        templates_resolved = False
        while 'template' in section:
            overrides.update(section.pop('overrides', {}))

            try:
                template = loader.templates.load(section.pop('template'))
            except Exception as e:
                loader.errors.append(f'{loader.source}, {file_name}, {sections_display}section #{section_index}: {e}')
                break

            errors = loader.templates.apply_overrides(template, overrides)
            if errors:
                override_errors.append((section_index, errors))

            if isinstance(template, dict):
                template.update(section)
                section = template
                sections[section_index - 1] = template
            elif isinstance(template, list):
                if template:
                    section = template[0]
                    for item_index, template_item in enumerate(template):
                        sections.insert(section_index + item_index, template_item)

                    # Delete what's at the current index
                    sections.pop(section_index - 1)

                    # Perform this check once again
                    if not isinstance(section, dict):
                        loader.errors.append(
                            '{}, {}, {}section #{}: Template section must be a mapping object'.format(
                                loader.source, file_name, sections_display, section_index
                            )
                        )
                        break
                else:
                    loader.errors.append(
                        '{}, {}, {}section #{}: Template refers to an empty array'.format(
                            loader.source, file_name, sections_display, section_index
                        )
                    )
                    break
            else:
                loader.errors.append(
                    '{}, {}, {}section #{}: Template does not refer to a mapping object nor array'.format(
                        loader.source, file_name, sections_display, section_index
                    )
                )
                break

        # Only set upon success or if there were no templates
        else:
            templates_resolved = True

        if not templates_resolved:
            continue

        MISSING = (
            f'{loader.source}, {file_name}, {sections_display}section #{section_index}: '
            'Every section must contain a `{{key}}` attribute'
        )
        INVALID = (
            f'{loader.source}, {file_name}, {sections_display}section #{section_index}: '
            'Attribute `{{key}}` must be a {{type}}'
        )

        # now validate the expanded section object
        _validate(section, validations, loader, MISSING, INVALID)

        section_name = section['name']
        if section_name in section_names_origin:
            loader.errors.append(
                '{}, {}, {}section #{}: section name `{}` already used by section #{}'.format(
                    loader.source,
                    file_name,
                    sections_display,
                    section_index,
                    section_name,
                    section_names_origin[section_name],
                )
            )
        else:
            section_names_origin[section_name] = section_index

        if 'sections' in section:
            nested_sections = section['sections']
            if not isinstance(nested_sections, list):
                loader.errors.append(
                    '{}, {}, {}{}: The `sections` attribute must be an array'.format(
                        loader.source, file_name, sections_display, section_name
                    )
                )
                continue

            previous_sections = list(prev_sections)
            previous_sections.append(section_name)
            section_validator(nested_sections, loader, file_name, *previous_sections)

    # If there are unused overrides, add the associated error messages
    if overrides:
        for section_index, errors in override_errors:
            error_message = '\n'.join(errors)
            loader.errors.append(
                f'{loader.source}, {file_name}, {sections_display}section #{section_index}: {error_message}'
            )
