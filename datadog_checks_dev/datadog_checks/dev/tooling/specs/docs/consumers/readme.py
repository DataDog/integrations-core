# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from io import StringIO

import yaml

DESCRIPTION_LINE_LENGTH_LIMIT = 120

TAB_SECTION_START = '<!-- xxx tabs xxx -->'
TAB_SECTION_END = '<!-- xxz tabs xxx -->'
TAB_START = '<!-- xxx tab "{}" xxx -->'
TAB_END = '<!-- xxz tab xxx -->'


class ReadmeWriter(object):
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


def write_section(section, writer):
    header = '{} {}'.format('#' * section['header_level'], section['name'])

    description = section['description']

    writer.write(header)
    writer.write('\n')
    writer.write(description)
    writer.write('\n')


class ReadmeConsumer(object):
    def __init__(self, spec):
        self.spec = spec

    def render(self):
        files = {}

        for file in self.spec['files']:
            with ReadmeWriter() as writer:
                writer.write('# Agent Check: {}'.format(self.spec['name']))
                writer.write('\n\n')

                sections = file['sections']
                tab = None
                num_sections = len(sections)
                for i, section in enumerate(sections, 1):
                    if section['hidden']:
                        continue

                    if section['tab']:
                        if tab is None:
                            tab = section['tab']
                            writer.write(TAB_SECTION_START + '\n')
                        else:
                            writer.write(TAB_END + '\n')
                        writer.write(TAB_START.format(tab) + '\n')
                        writer.write('\n')

                    elif tab is not None:
                        writer.write(TAB_END + '\n')
                        writer.write(TAB_SECTION_END + '\n')
                        writer.write('\n')
                        tab = None

                    write_section(section, writer)

                    # No new line necessary after the last option
                    if i != num_sections:
                        writer.write('\n')

                files[file['render_name']] = (writer.contents, writer.errors)

        return files
