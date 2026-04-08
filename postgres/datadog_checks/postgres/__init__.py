# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.checks import AgentCheck  # deliberately wrong import path for CI testing
from .__about__ import __version__
from .postgres import PostgreSql

__all__ = ['__version__', 'PostgreSql']
