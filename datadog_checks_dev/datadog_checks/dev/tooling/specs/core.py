# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import yaml


class BaseSpec(object):
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
        self.data = None
        self.errors = []

        # To be overridden in subclasses
        self.spec_type = None
        self.templates = None
        self.validator = None

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
            # spec has already been validated
            return

        try:
            self.data = yaml.safe_load(self.contents)
        except Exception as e:
            self.errors.append(f'{self.source}: Unable to parse the configuration specification: {e}')
            return

        self.validate()

    def validate(self):
        # for subclasses to override
        raise NotImplementedError()

    def is_valid(self):
        return not self.errors
