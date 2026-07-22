# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# Authored by Ed Ferron
from .__about__ import __version__
from .check import GenesysMosCheck

__all__ = ["__version__", "GenesysMosCheck"]
