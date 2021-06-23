# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
from collections import deque

import markdown
from markdown.blockprocessors import ReferenceProcessor

from ....utils import get_parent_dir, path_join
from ..core import BaseSpec
from ..templates import BaseTemplate
from .spec import spec_validator

# Match markdown reference links - [text][number-ref]
# the `?` after `[\s\S]+` will match lazily vs greedily
MATCH_REF = re.compile(r"(\[[\s\S]+?\])\s*(\[\d+\])")


class DocsTemplates(BaseTemplate):
    TEMPLATES_DIR = path_join(get_parent_dir(get_parent_dir(get_parent_dir(__file__))), 'templates', 'docs')


class DocsSpec(BaseSpec):
    def __init__(self, contents, template_paths=None, source=None, version=None):
        super().__init__(contents, template_paths, source, version)

        self.spec_type = 'Docs'
        self.templates = DocsTemplates(template_paths)

    def validate(self):
        spec_validator(self.data, self)
        if self.errors:
            return
        self.normalize_links()

    def normalize_links(self):
        """Translate all reference-style links to inline links."""
        # Markdown doc reference: https://www.markdownguide.org/basic-syntax/#links

        for fidx, file in enumerate(self.data['files'], 1):
            sections = deque(enumerate(file['sections'], 1))
            while sections:
                sidx, section = sections.popleft()
                section['prepend_text'] = self._normalize(section['prepend_text'], fidx, sidx)
                section['description'] = self._normalize(section['description'], fidx, sidx)
                section['append_text'] = self._normalize(section['append_text'], fidx, sidx)
                if 'sections' in section:
                    nested_sections = [
                        (f'{sidx}.{subidx}', subsection) for subidx, subsection in enumerate(section['sections'], 1)
                    ]
                    # extend left backwards for correct order of sections
                    sections.extendleft(nested_sections[::-1])

    def _normalize(self, text, fidx, sidx):
        # use the markdown internal processor class to extract all references into a dict
        m = markdown.Markdown()

        def process_references(txt):
            blocks = [txt]
            while ReferenceProcessor(m.parser).run(None, blocks):
                blocks = ['\n'.join(blocks)]
            return blocks[0], m.parser.md.references

        p, refs = process_references(text)

        # test that we extracted appropriately
        matches = MATCH_REF.findall(p)
        if len(matches) != len(refs):
            # attach validation error
            err = (
                f'In file #{fidx}, section #{sidx}: found {len(matches)} reference links, '
                f'but extracted {len(refs)} references.'
            )
            self.errors.append(err)
            return text

        # Translate refs to text that is directly replacable
        #  {'1': ('https://datadoghq.com', None),
        #   '2': ('https://google.com', "Google Link")}

        # To:
        #  {'[1]': '(https://datadoghq.com)',
        #   '[2]': '(https://google.com "Google Link")'}
        inline_links = {}
        for k, v in refs.items():
            link = v[0]
            if v[1] is not None:
                link += f'"{v[1]}"'
            inline_links[f'[{k}]'] = f'({link})'

        inline_md = MATCH_REF.sub(lambda x: '{}{}'.format(x.group(1), inline_links[x.group(2)]), p)
        return inline_md
