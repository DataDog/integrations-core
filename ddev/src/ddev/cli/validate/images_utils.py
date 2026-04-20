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
from pathlib import Path

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


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a docker-compose-style `.env` file. Missing file yields empty dict."""
    if not path.is_file():
        return {}
    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        result[key] = value
    return result
