# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ....utils import get_parent_dir, path_join
from ..core import BaseSpec
from ..templates import BaseTemplate
from .spec import spec_validator


class ConfigTemplates(BaseTemplate):
    TEMPLATES_DIR = path_join(get_parent_dir(get_parent_dir(get_parent_dir(__file__))), 'templates', 'configuration')


class ConfigSpec(BaseSpec):
    def __init__(self, contents, template_paths=None, source=None, version=None):
        super().__init__(contents, template_paths, source, version)

        self.spec_type = 'Configuration'
        self.templates = ConfigTemplates(template_paths)

    def validate(self):
        spec_validator(self.data, self)
