# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import yaml

from .spec import spec_validator
from .template import ConfigTemplates


class ConfigSpec(object):
    def __init__(self, contents, template_paths=None, source=None, version=None):
        """
        **Parameters:**
        - **contents** (_str_) - the raw text contents of a spec
        - **template_paths** (_list_) - a sequence of directories that will take precedence when looking for templates
        - **source** (_str_) - a textual representation of what the spec refers to, usually an integration name
        - **version** (_str_) - the version of the spec to default to if the spec does not define one
        """
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
        If the `errors` attribute is empty after this is called, the `data` attribute
        will be the fully resolved spec object.
        """
        if self.data is not None and not self.errors:
            return self.data

        try:
            self.data = yaml.safe_load(self.contents)
        except Exception as e:
            self.errors.append(f'{self.source}: Unable to parse the configuration specification: {e}')
            return

        return spec_validator(self.data, self)
