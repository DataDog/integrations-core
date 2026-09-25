# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Naming rules for integrations, shared by every component that has to agree on them.
"""

from __future__ import annotations

import re
from pathlib import PurePath

VALID_INTEGRATION_NAME = re.compile(r'^[A-Z0-9](?:[A-Z0-9._\- ]*[A-Z0-9])?$', re.IGNORECASE)


def is_valid_integration_name(name: str) -> bool:
    """Return True iff `name` is acceptable to `normalize_project_name` / scaffold path templating.

    Must contain only ASCII letters/digits, dots, hyphens, underscores, or spaces, and must
    begin and end with an alphanumeric character.
    """
    return bool(VALID_INTEGRATION_NAME.match(name))


def is_creatable_integration_name(name: str) -> bool:
    """Return True iff `ddev create` would accept `name` as a new integration name.

    This is the full policy `_validate_integration_name` (`ddev/cli/create/_common.py`)
    enforces: the character-set check above, plus the reserved `datadog` prefix. Callers
    outside the CLI must use this rather than `is_valid_integration_name` alone, or a name
    that only fails the reserved-prefix rule would slip through unrejected.
    """
    return is_valid_integration_name(name) and not name.lower().startswith('datadog')


def integration_dir_name(name: str) -> str:
    """Return the directory name `ddev create` gives the integration called `name`.

    Single source of truth for the name -> directory mapping. Every caller that needs to
    know where an integration lives on disk must go through this function, so the mapping
    cannot drift between the scaffolder that creates the directory and the consumers that
    later read from or delete within it.

    Raises `ValueError` if `name` is not a name `ddev create` would accept, or if it does
    not normalize to a single path segment.
    """
    if not isinstance(name, str) or not is_creatable_integration_name(name):
        raise ValueError(f'Invalid integration name: {name!r}')

    normalized = normalize_package_name(name)
    # Defence in depth for callers that join the result onto a root directory: a separator
    # would let `name` designate a location outside that root. `is_creatable_integration_name`
    # already rejects every character that could produce one, so this guard exists to keep the
    # single-segment invariant owned here rather than assumed by each caller.
    if len(PurePath(normalized).parts) != 1:
        raise ValueError(f'Invalid integration name: {name!r}')

    return normalized


def normalize_package_name(name: str) -> str:
    """Lowercase and collapse separators to underscore (used for directory and Python package names)."""
    return re.sub(r'[-_. ]+', '_', name).lower()


def normalize_project_name(name: str) -> str:
    """Normalize per PEP 503 for use as a distribution name."""
    if not re.search(r'^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$', name, re.IGNORECASE):
        raise ValueError('Project name must only contain ASCII letters/digits, underscores, hyphens, and periods.')
    return re.sub(r'[-_.]+', '-', name).lower()


def kebab_case_name(name: str) -> str:
    """Lowercase and replace separators with hyphens."""
    return re.sub(r'[_ ]', '-', name.lower())


def normalize_display_name(display_name: str) -> str:
    """Lower-case, collapse runs of non-alphanumeric characters to underscores, strip leading/trailing underscores."""
    normalized = re.sub(r'[^0-9A-Za-z-]', '_', display_name)
    normalized = re.sub(r'_+', '_', normalized).strip('_')
    return normalized.lower()
