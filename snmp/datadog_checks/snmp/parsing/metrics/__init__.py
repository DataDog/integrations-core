# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Helpers for parsing the `metrics` section of a config file.
"""
from .metrics import parse_metrics

__all__ = ["parse_metrics"]
