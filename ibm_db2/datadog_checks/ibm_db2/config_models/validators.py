# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .instance import InstanceConfig


def check_instance(config: InstanceConfig) -> InstanceConfig:
    if config.collect_schemas is None or config.collect_schemas.collection_interval is None:
        return config
    interval = config.collect_schemas.collection_interval
    if not math.isfinite(interval) or not math.isfinite(1 / interval):
        raise ValueError('collect_schemas.collection_interval must be finite with a finite collection rate')
    return config
