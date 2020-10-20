# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .spec import spec_validator
from ..core import BaseSpec
from ..templates import BaseTemplate
from ....utils import get_parent_dir, path_join


class DocsTemplates(BaseTemplate):
    TEMPLATES_DIR = path_join(get_parent_dir(get_parent_dir(get_parent_dir(__file__))), 'templates', 'docs')


class DocsSpec(BaseSpec):
    def __init__(self, contents, template_paths=None, source=None, version=None):
        super().__init__(contents, template_paths, source, version)

        self.spec_type = 'Docs'
        self.templates = DocsTemplates(template_paths)

    def validate(self):
        spec_validator(self.data, self)
