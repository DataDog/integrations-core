# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from click.testing import CliRunner as __CliRunner
from click.testing import Result


class CliRunner(__CliRunner):
    def __init__(self, command):
        super().__init__()
        self._command = command

    def __call__(self, *args, **kwargs) -> Result:
        # Exceptions should always be handled
        kwargs.setdefault("catch_exceptions", False)

        return self.invoke(self._command, args, **kwargs)
