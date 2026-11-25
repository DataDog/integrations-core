# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class RunAbortError(Exception):
    """Stop the run without returning the failure to the model as a tool result."""
