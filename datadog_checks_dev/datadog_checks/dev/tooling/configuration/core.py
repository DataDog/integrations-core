# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import yaml

from .spec import spec_validator
from .template import ConfigTemplates


class ConfigSpec(object):
    def __init__(self, contents, template_paths=None, source=None, version=None):
        self.contents = contents
        self.source = source
        self.version = version
        self.templates = ConfigTemplates(template_paths)
        self.data = None
        self.errors = []

    def load(self):
        """
        This function de-serializes the specification and:

        1. fills in default values
        2. populates any selected templates
        3. accumulates all error/warning messages
        """
        if self.data is not None and not self.errors:
            return self.data

        try:
            self.data = yaml.safe_load(self.contents)
        except Exception as e:
            self.errors.append(f'{self.source}: Unable to parse the configuration specification: {e}')
            return

        return spec_validator(self.data, self)
