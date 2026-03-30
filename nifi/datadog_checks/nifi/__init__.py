# ABOUTME: Entry point for the NiFi Datadog integration package.
# ABOUTME: Exposes NifiCheck and package version for agent discovery.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .check import NifiCheck

__all__ = ['__version__', 'NifiCheck']
