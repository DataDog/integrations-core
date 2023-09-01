# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pluggy

spec = pluggy.HookspecMarker('ddev')


@spec
def register_commands():
    """Register new commands with the CLI."""
