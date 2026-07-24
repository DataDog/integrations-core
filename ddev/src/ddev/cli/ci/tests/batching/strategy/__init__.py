# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Batching strategies: the extension contract and the default implementation.

A strategy maps an ordered list of concrete jobs to an ordered list of capacity-bounded job groups.
The package stays small so that adding a strategy means adding one module beside
:mod:`~ddev.cli.ci.tests.batching.strategy.default`:

- :mod:`~ddev.cli.ci.tests.batching.strategy.types` — the injectable ``BatchStrategy`` protocol.
- :mod:`~ddev.cli.ci.tests.batching.strategy.default` — the default packing strategy.

Shared planning exceptions, partition validation, and ``TestBatch`` construction are not strategy
concerns; they live one level up in :mod:`~ddev.cli.ci.tests.batching.exceptions`,
:mod:`~ddev.cli.ci.tests.batching.validation`, and :mod:`~ddev.cli.ci.tests.batching.assembly`.
"""

from __future__ import annotations

from ddev.cli.ci.tests.batching.strategy.default import default_strategy
from ddev.cli.ci.tests.batching.strategy.types import BatchStrategy

__all__ = [
    "BatchStrategy",
    "default_strategy",
]
