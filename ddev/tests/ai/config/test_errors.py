# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from ddev.ai.config.errors import ErrorKind
from ddev.ai.config.registry import ResourceKind


def test_every_resource_kind_maps_to_an_error_kind():
    """ErrorKind.for_resource relies on ErrorKind reusing every ResourceKind value."""
    for kind in ResourceKind:
        assert ErrorKind.for_resource(kind).value == kind.value
