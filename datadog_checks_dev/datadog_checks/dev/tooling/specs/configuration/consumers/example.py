# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from io import StringIO

import yaml

DESCRIPTION_LINE_LENGTH_LIMIT = 120


class OptionWriter(object):
    def __init__(self):
        self.writer = StringIO()
        self.errors = []

    def write(self, *strings):
        for s in strings:
            self.writer.write(s)

    def new_error(self, s):
        self.errors.append(s)

    @property
    def contents(self):
        return self.writer.getvalue()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.writer.close()


def construct_yaml(obj, **kwargs):
    kwargs.setdefault('default_flow_style', False)
    return yaml.safe_dump(obj, sort_keys=False, **kwargs)


def value_type_string(value):
    if 'oneOf' in value:
        return ' or '.join(value_type_string(type_data) for type_data in value['oneOf'])
    else:
        value_type = value['type']
        if value_type == 'object':
            return 'mapping'
        elif value_type == 'array':
            item_type = value['items']['type']
            if item_type == 'object':
                return 'list of mappings'
            elif item_type == 'array':
                return 'list of lists'
            else:
                return f'list of {item_type}s'
        else:
            return value_type


def option_enabled(option):
    if 'enabled' in option:
        return bool(option['enabled'])

    return option['required']


def write_description(option, writer, indent, option_type):
    description = option['description']
    deprecation = option['deprecation']
    if deprecation:
        description += '\n\n<<< DEPRECATED >>>\n\n'
        for key, info in option['deprecation'].items():
            key_part = f'{key}: '
            info_pad = ' ' * len(key_part)
            description += key_part

            for i, line in enumerate(info.splitlines()):
                if i > 0:
                    description += info_pad

                description += f'{line}\n'

    for line in description.splitlines():
        if line:
            line = f'{indent}## {line}'
            if len(line) > DESCRIPTION_LINE_LENGTH_LIMIT and ' /noqa' not in line:
                extra_characters = len(line) - DESCRIPTION_LINE_LENGTH_LIMIT
                writer.new_error(
                    'Description line length of {} `{}` was over the limit by {} character{}'.format(
                        option_type, option['name'], extra_characters, 's' if extra_characters > 1 else ''
                    )
                )
            elif ' /noqa' in line:
                line = line.replace(' /noqa', '')
            writer.write(line)
        else:
            writer.write(indent, '##')

        writer.write('\n')


def write_option(option, writer, indent='', start_list=False):
    option_name = option['name']
    if 'value' in option:
        value = option['value']
        required = option['required']
        writer.write(
            indent,
            '## @param ',
            option_name,
            ' - ',
            value_type_string(value),
            ' - ',
            'required' if required else 'optional',
        )

        example = value.get('example')
        example_type = type(example)
        if not required:
            if 'default' in value:
                default = value['default']
                default_type = type(default)
                if default is not None and str(default).lower() != 'none':
                    if default_type is str:
                        writer.write(' - default: ', default)
                    elif default_type is bool:
                        writer.write(' - default: ', 'true' if default else 'false')
                    else:
                        writer.write(' - default: ', repr(default))
            else:
                if example_type is bool:
                    writer.write(' - default: ', 'true' if example else 'false')
                elif example_type in (int, float):
                    writer.write(' - default: ', str(example))
                elif example_type is str:
                    if example and not (example[0] == '<' and example[-1] == '>'):
                        writer.write(' - default: ', example)

        writer.write('\n')

        write_description(option, writer, indent, 'option')

        writer.write(indent, '#\n')

        if start_list:
            option_yaml = construct_yaml([{option_name: example}])
            indent = indent[:-2]
        else:
            if value.get('compact_example') and example_type is list:
                option_yaml_lines = [f'{option_name}:']
                for item in example:
                    # Solitary strings are given an ellipsis after, prevent that
                    if isinstance(item, str):
                        compacted_item = construct_yaml(item, default_flow_style=True, default_style='"')
                    else:
                        # Compact examples should stay on one line to prevent weird line wraps.
                        compacted_item = construct_yaml(item, default_flow_style=True, width=float('inf'))

                    option_yaml_lines.append(f'- {compacted_item.strip()}')

                option_yaml = '\n'.join(option_yaml_lines)
            else:
                option_yaml = construct_yaml({option_name: example})

        example_indent = '  ' if example_type is list and example else ''
        for i, line in enumerate(option_yaml.splitlines()):
            writer.write(indent)
            if not option_enabled(option):
                writer.write('# ')

            if i > 0:
                writer.write(example_indent)

            writer.write(line, '\n')
    else:
        write_description(option, writer, indent, 'section')

        writer.write(indent, '#\n')

        if 'options' in option:
            multiple = option['multiple']
            options = sorted(option['options'], key=lambda opt: -opt['display_priority'])
            next_indent = indent + '    '
            writer.write(indent, option_name, ':', '\n')
            if options:
                for i, opt in enumerate(options):
                    if opt['hidden']:
                        continue

                    writer.write('\n')
                    if i == 0 and multiple:
                        if option_enabled(opt):
                            write_option(opt, writer, next_indent, start_list=True)
                        else:
                            writer.write(next_indent[:-2], '-\n')
                            write_option(opt, writer, next_indent)
                    else:
                        write_option(opt, writer, next_indent)
            elif multiple:
                writer.write('\n', next_indent[:-2], '- {}\n')

        # For sections that prefer to document everything in the description, like `logs`
        else:
            example = option.get('example', [] if option.get('multiple', False) else {})
            option_yaml = construct_yaml({option_name: example})

            example_indent = '  ' if type(example) is list and example else ''
            for i, line in enumerate(option_yaml.splitlines()):
                if not option_enabled(option):
                    writer.write(indent, '# ')

                if i > 0:
                    writer.write(example_indent)

                writer.write(line, '\n')


class ExampleConsumer(object):
    def __init__(self, spec):
        self.spec = spec

    def render(self):
        files = {}

        for file in self.spec['files']:
            with OptionWriter() as writer:
                options = file['options']
                num_options = len(options)
                for i, option in enumerate(options, 1):
                    if option['hidden']:
                        continue

                    write_option(option, writer)

                    # No new line necessary after the last option
                    if i != num_options:
                        writer.write('\n')

                files[file['example_name']] = (writer.contents, writer.errors)

        return files
