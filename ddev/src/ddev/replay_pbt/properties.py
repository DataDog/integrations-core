# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Shared names for cached replay PBT properties.

The replay-PBT CLI and pytest module need to agree on the same small set of
property identifiers. Keeping them in a StrEnum avoids duplicated string
constants while still letting Click and environment variables use plain string
values at process boundaries.
"""

from __future__ import annotations

from enum import StrEnum


class ReplayPBTProperty(StrEnum):
    DETERMINISTIC = 'deterministic'
    OPENMETRICS_LABEL_ORDER = 'openmetrics-label-order'


REPLAY_PBT_PROPERTY_CHOICES = tuple(prop.value for prop in ReplayPBTProperty)
