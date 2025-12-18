# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
DynamicD: Smart fake data generator for Datadog integrations.

Uses Claude API to generate realistic, scenario-rich telemetry simulators
based on integration metadata.
"""

from ddev.cli.meta.scripts.dynamicd.cli import dynamicd

__all__ = ['dynamicd']

