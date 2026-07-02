# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations


class FlowConfigError(Exception):
    """Wraps Pydantic ValidationError or YAML errors with a user-friendly message."""
