# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Helpers to parse the `metric_tags` section of a config file.
"""
from .metric_tags import parse_metric_tags

__all__ = ["parse_metric_tags"]
