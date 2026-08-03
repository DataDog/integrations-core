# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Async GitHub REST API client.

Typical usage::

    from ddev.utils.github_async import async_github_client
    from ddev.utils.github_async.models import PullRequest

    async with async_github_client(token=my_token) as client:
        response = await client.create_pull_request(...)

Both this package's top-level symbols and the ``models`` subpackage use PEP 562
``__getattr__`` to load submodules on demand. Importing a model from
``ddev.utils.github_async.models`` does not load the HTTP client (so ``httpx``
stays out of ``sys.modules`` for callers that only need the types).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Re-exports for type checkers / IDE autocomplete only; do not execute at runtime.
    # The `X as X` aliases mark these as explicit re-exports for linters.
    from .client import DEFAULT_BASE_URL as DEFAULT_BASE_URL
    from .client import GITHUB_API_VERSION as GITHUB_API_VERSION
    from .client import AsyncGitHubClient as AsyncGitHubClient
    from .client import GitHubResponse as GitHubResponse
    from .client import PaginationData as PaginationData
    from .client import async_github_client as async_github_client

# Map of exported name -> submodule (relative to this package) that defines it.
MODULE_BY_NAME: dict[str, str] = {
    'AsyncGitHubClient': 'client',
    'async_github_client': 'client',
    'GITHUB_API_VERSION': 'client',
    'DEFAULT_BASE_URL': 'client',
    'GitHubResponse': 'client',
    'PaginationData': 'client',
}


def __getattr__(name: str) -> Any:
    try:
        module_name = MODULE_BY_NAME[name]
    except KeyError:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}') from None

    import importlib

    module = importlib.import_module(f'.{module_name}', __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | MODULE_BY_NAME.keys())


__all__ = sorted(MODULE_BY_NAME)
