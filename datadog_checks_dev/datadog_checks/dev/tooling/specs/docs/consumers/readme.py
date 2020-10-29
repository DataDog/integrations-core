# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from io import StringIO

DESCRIPTION_LINE_LENGTH_LIMIT = 120

TAB_SECTION_START = '<!-- xxx tabs xxx -->'
TAB_SECTION_END = '<!-- xxz tabs xxx -->'
TAB_START = '<!-- xxx tab "{}" xxx -->'
TAB_END = '<!-- xxz tab xxx -->'

INLINE_REF = re.compile(r"(\[[\s\S]+?\])\s*(\(.*?\))")


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


def update_links(link, links):
    newref = max(links.values() or [0]) + 1
    links[link] = newref


def process_links(section, links):
    """Extract inline links and replace with references."""

    text = section['description']

    matches = INLINE_REF.findall(text)

    for m in matches:
        lnk = m[1]
        if lnk not in links:
            update_links(lnk, links)

    # replace (link) with [ref]
    newtext = INLINE_REF.sub(lambda x: '{}[{}]'.format(x.group(1), links[x.group(2)]), text)
    section['description'] = newtext


def write_section(section, writer):
    header = '{} {}'.format('#' * section['header_level'], section['name'])

    description = section['description']

    writer.write(header)
    writer.write('\n\n')
    writer.write(description)
    writer.write('\n')


def get_references(links):
    refs = []
    for link, ref in links.items():
        line = f"[{ref}]: {link.lstrip('(').rstrip(')')}"
        refs.append(line)
    return '\n'.join(refs)


class ReadmeConsumer(object):
    def __init__(self, spec):
        self.spec = spec

    def render(self):
        files = {}

        for file in self.spec['files']:
            with ReadmeWriter() as writer:
                links = dict()

                writer.write('# Agent Check: {}'.format(self.spec['name']))
                writer.write('\n\n')

                sections = file['sections']
                tab = None
                for section in sections:
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

                    process_links(section, links)
                    write_section(section, writer)

                    writer.write('\n')

                # add link references to the end of document
                refs = get_references(links)
                writer.write(refs)

                files[file['render_name']] = (writer.contents, writer.errors)

        return files
