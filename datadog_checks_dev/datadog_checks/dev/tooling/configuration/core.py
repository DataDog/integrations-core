# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import yaml

from .spec import spec_validator
from .template import ConfigTemplates


class ConfigSpec(object):
    def __init__(self, contents, source=None, template_paths=None):
        self.contents = contents
        self.source = source
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
            self.errors.append('{}: Unable to parse the configuration specification: {}'.format(self.source, e))
            return

        return spec_validator(self.data, self)
