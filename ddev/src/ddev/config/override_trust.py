# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import hashlib
import json

from ddev.utils.fs import Path

TRUSTED_OVERRIDES_FILENAME = "trusted_overrides.json"


def strip_fetch_command_fields(data: dict) -> list[str]:
    """Recursively remove all keys ending with ``_fetch_command`` from *data* (in-place).

    Returns a list of the dotted paths that were stripped, e.g. ``["github.user_fetch_command"]``.
    """
    stripped: list[str] = []
    _strip_fetch_command_fields_recursive(data, [], stripped)
    return stripped


def _strip_fetch_command_fields_recursive(data: dict, path: list[str], stripped: list[str]) -> None:
    keys_to_delete = [k for k in data if isinstance(k, str) and k.endswith('_fetch_command')]
    for key in keys_to_delete:
        stripped.append('.'.join([*path, key]))
        del data[key]

    for key, value in list(data.items()):
        if isinstance(value, dict):
            _strip_fetch_command_fields_recursive(value, [*path, key], stripped)


def _compute_file_hash(path: Path) -> str:
    """Return the SHA-256 hex digest of *path*'s contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _trusted_overrides_path(global_config_dir: Path) -> Path:
    return global_config_dir / TRUSTED_OVERRIDES_FILENAME


def _load_trust_store(global_config_dir: Path) -> dict:
    """Load ``trusted_overrides.json`` as a dict, returning ``{}`` if missing or corrupt."""
    trust_file = _trusted_overrides_path(global_config_dir)
    if not trust_file.is_file():
        return {}
    try:
        return json.loads(trust_file.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_trust_store(global_config_dir: Path, store: dict) -> None:
    trust_file = _trusted_overrides_path(global_config_dir)
    trust_file.ensure_parent_dir_exists()
    trust_file.write_atomic(json.dumps(store, indent=2), 'w', encoding='utf-8')


def get_override_trust_state(overrides_path: Path, global_config_dir: Path) -> tuple[str, str]:
    """Return ``(state, file_hash)`` for *overrides_path*.

    *state* is one of: ``'allowed'``, ``'denied'``, ``'unknown'``.
    *file_hash* is the current SHA-256 of the file (always computed).
    """
    current_hash = _compute_file_hash(overrides_path)
    store = _load_trust_store(global_config_dir)
    key = str(overrides_path)
    entry = store.get(key)
    if not entry or not isinstance(entry, dict):
        return 'unknown', current_hash
    recorded_hash = entry.get('hash', '')
    state = entry.get('state', 'unknown')
    if recorded_hash != current_hash:
        return 'unknown', current_hash
    return state, current_hash


def upsert_trust_entry(overrides_path: Path, global_config_dir: Path, state: str) -> None:
    """Write or update the trust record for *overrides_path* with the current hash."""
    current_hash = _compute_file_hash(overrides_path)
    store = _load_trust_store(global_config_dir)
    store[str(overrides_path)] = {'hash': current_hash, 'state': state}
    _save_trust_store(global_config_dir, store)

