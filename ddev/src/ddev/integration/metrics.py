# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pydantic import BaseModel


class Metric(BaseModel):
    metric_name: str
    metric_type: str
    interval: int | None
    unit_name: str
    per_unit_name: str
    description: str
    orientation: int | None
    integration: str
    short_name: str
    curated_metric: str
