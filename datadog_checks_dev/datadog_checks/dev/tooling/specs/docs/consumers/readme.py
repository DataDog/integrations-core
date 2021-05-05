# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from collections import deque
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
    # these are the attributes in each section that can contain links
    text_attributes = ['prepend_text', 'description', 'append_text']

    for attribute in text_attributes:
        text = section[attribute]

        matches = INLINE_REF.findall(text)

        for m in matches:
            lnk = m[1]
            if lnk not in links:
                update_links(lnk, links)

        # replace (link) with [ref]
        newtext = INLINE_REF.sub(lambda x: '{}[{}]'.format(x.group(1), links[x.group(2)]), text)
        section[attribute] = newtext


def write_section(section, writer):
    header = '{} {}'.format('#' * section['header_level'], section['name'])
    prepend_text = section['prepend_text']
    description = section['description']
    append_text = section['append_text']

    writer.write(header)
    writer.write('\n\n')
    if prepend_text:
        writer.write(prepend_text)
        writer.write('\n\n')
    writer.write(description)
    if append_text:
        writer.write('\n\n')
        writer.write(append_text)
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

                sections = deque(file['sections'])
                tab_section_end = None
                while sections:
                    section = sections.popleft()
                    if section['hidden']:
                        continue

                    if section['tab']:
                        tab = section['tab']
                        if tab_section_end is None:
                            # find which section stops having 'tab'
                            for s in sections:
                                if not s['tab']:
                                    tab_section_end = s
                                    break
                            else:
                                # tabs continue until end of sections
                                # add a flag to close at end of all sections
                                tab_section_end = 'EOL'
                            writer.write(TAB_SECTION_START + '\n')
                        else:
                            writer.write(TAB_END + '\n')
                        writer.write(TAB_START.format(tab) + '\n')
                        writer.write('\n')

                    elif section == tab_section_end:
                        writer.write(TAB_END + '\n')
                        writer.write(TAB_SECTION_END + '\n')
                        writer.write('\n')
                        tab_section_end = None

                    process_links(section, links)
                    write_section(section, writer)

                    writer.write('\n')

                    if 'sections' in section:
                        # extend left backwards for correct order of sections
                        # eg sections.extendleft([s2.1, s2.2]) updates section to [s2.2, s2.1, s3]
                        # so we need to reverse it for correctness
                        sections.extendleft(section['sections'][::-1])

                # close tabs section if never got closed
                if tab_section_end:
                    writer.write(TAB_END + '\n')
                    writer.write(TAB_SECTION_END + '\n')
                    writer.write('\n')
                    tab_section_end = None

                # add link references to the end of document
                refs = get_references(links)
                writer.write(refs)

                files[file['render_name']] = (writer.contents, writer.errors)

        return files
