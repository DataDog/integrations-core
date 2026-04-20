# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Scanner, env-var resolver, and manifest helpers for `ddev validate images`.

Public surface:
  scan_repo(app) -> Manifest
  load_manifest(path) -> Manifest
  write_manifest(path, manifest) -> None
  diff_manifests(old, new) -> ManifestDiff
  classify(image, prefixes) -> bool
"""
from __future__ import annotations

import re

_ENV_VAR_RE = re.compile(
    r'''
    \$\$                                   # escaped $$ -> literal $
    | \$\{([A-Za-z_][A-Za-z0-9_]*)         # ${VAR
         (?: (:?-) ([^}]*) )?              #   optional default with :-/-
       \}
    | \$([A-Za-z_][A-Za-z0-9_]*)           # $VAR
    ''',
    re.VERBOSE,
)


def substitute_env_vars(template: str, context: dict[str, str]) -> str | None:
    """Resolve docker-compose-style env-var references in `template`.

    Returns the resolved string, or None if any reference cannot be resolved.
    """
    unresolved = False

    def repl(match: re.Match[str]) -> str:
        nonlocal unresolved
        whole = match.group(0)
        if whole == '$$':
            return '$'
        braced_name = match.group(1)
        op = match.group(2)
        default = match.group(3)
        bare_name = match.group(4)
        name = braced_name or bare_name
        value = context.get(name)
        if op == ':-':
            if not value:
                return default if default is not None else ''
            return value
        if op == '-':
            if value is None:
                return default if default is not None else ''
            return value
        if value is None:
            unresolved = True
            return ''
        return value

    result = _ENV_VAR_RE.sub(repl, template)
    return None if unresolved else result
