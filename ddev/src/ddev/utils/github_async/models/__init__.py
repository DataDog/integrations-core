# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Lazy re-exports for the async GitHub client's domain models.

Each model class lives in its own submodule (e.g. ``pull_request.py``). The
re-exports below let callers write::

    from ddev.utils.github_async.models import PullRequest

without having to know which submodule the class lives in, and without
eagerly importing every submodule when only one is used.

Mechanism: PEP 562's module-level ``__getattr__`` hook. The first time a
name is accessed, the matching submodule is imported on demand and the
resolved attribute is cached on the package so subsequent accesses are free.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Re-exports for type checkers / IDE autocomplete. These imports do not
    # execute at runtime (they live behind `TYPE_CHECKING`), so they do not
    # break the lazy-loading guarantee. The `X as X` aliases mark these as
    # explicit re-exports for linters.
    from .comment import IssueComment as IssueComment
    from .comment import PullRequestReviewComment as PullRequestReviewComment
    from .label import Label as Label
    from .pull_request import PullRequest as PullRequest
    from .pull_request import PullRequestRef as PullRequestRef
    from .user import GitHubUser as GitHubUser
    from .workflow import Artifact as Artifact
    from .workflow import ArtifactsList as ArtifactsList
    from .workflow import WorkflowRun as WorkflowRun

# Map of exported attribute name -> submodule (relative to this package) that
# defines it. Submodules are imported on demand by `__getattr__`.
MODULE_BY_NAME: dict[str, str] = {
    'Artifact': 'workflow',
    'ArtifactsList': 'workflow',
    'GitHubUser': 'user',
    'IssueComment': 'comment',
    'Label': 'label',
    'PullRequest': 'pull_request',
    'PullRequestRef': 'pull_request',
    'PullRequestReviewComment': 'comment',
    'WorkflowRun': 'workflow',
}


def __getattr__(name: str) -> Any:
    try:
        module_name = MODULE_BY_NAME[name]
    except KeyError:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}') from None

    import importlib

    module = importlib.import_module(f'.{module_name}', __name__)
    value = getattr(module, name)
    # Cache so subsequent `from .models import Foo` is a plain dict lookup.
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | MODULE_BY_NAME.keys())


__all__ = sorted(MODULE_BY_NAME)
