# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import yaml

from ddev.validation.configuration.spec import spec_validator
from ddev.validation.configuration.template import ConfigTemplates


class ConfigSpec:
    def __init__(
        self,
        contents: str,
        template_paths: list[str] | None = None,
        source: str | None = None,
        version: str | None = None,
    ):
        """
        Parameters:

            contents:
                the raw text contents of a spec
            template_paths:
                a sequence of directories that will take precedence when looking for templates
            source:
                a textual representation of what the spec refers to, usually an integration name
            version:
                the version of the spec to default to if the spec does not define one
        """
        self.contents = contents
        self.source = source
        self.version = version
        self.templates = ConfigTemplates(template_paths)
        self.data: dict | None = None
        self.errors: list[str] = []

    def load(self) -> None:
        """
        This function de-serializes the specification and:
        1. fills in default values
        2. populates any selected templates
        3. accumulates all error/warning messages
        If the `errors` attribute is empty after this is called, the `data` attribute
        will be the fully resolved spec object.
        """
        if self.data is not None and not self.errors:
            return

        try:
            self.data = yaml.safe_load(self.contents)
        except Exception as e:
            self.errors.append(f'{self.source}: Unable to parse the configuration specification: {e}')
            return

        spec_validator(self.data, self)
