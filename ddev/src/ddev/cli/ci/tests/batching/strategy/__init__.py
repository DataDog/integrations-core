# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Batching strategies: the `BatchStrategy` contract and the default implementation.

Adding a strategy means adding one module here; validation and message construction live one
level up and apply to every strategy.
"""

from __future__ import annotations

from ddev.cli.ci.tests.batching.strategy.default import default_strategy
from ddev.cli.ci.tests.batching.strategy.types import BatchStrategy

__all__ = [
    "BatchStrategy",
    "default_strategy",
]
