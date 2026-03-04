# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any

from ddev.config.constants import ConfigEnvVars
from ddev.utils.fs import Path
from ddev.utils.toml import dumps_toml_data, load_toml_data

TRUST_STORE_FILENAME = 'trusted-local-configs.toml'


@dataclass(frozen=True)
class TrustRecord:
    path: str
    sha256: str


def get_trust_store_path() -> Path:
    from platformdirs import user_data_dir

    data_dir = Path(os.getenv(ConfigEnvVars.DATA) or user_data_dir('ddev', appauthor=False)).expand()
    return data_dir / TRUST_STORE_FILENAME


def local_config_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_local_config_path(path: Path) -> str:
    return str(path.expand().resolve())


def load_trust_records(trust_store_path: Path | None = None) -> dict[str, TrustRecord]:
    path = trust_store_path or get_trust_store_path()
    if not path.is_file():
        return {}

    try:
        trust_data = load_toml_data(path.read_text())
    except Exception:
        return {}

    records: dict[str, TrustRecord] = {}
    for item in trust_data.get('records', []):
        if not isinstance(item, dict):
            continue

        record_path = item.get('path')
        record_hash = item.get('sha256')
        if isinstance(record_path, str) and isinstance(record_hash, str):
            records[record_path] = TrustRecord(path=record_path, sha256=record_hash)

    return records


def save_trust_records(records: dict[str, TrustRecord], trust_store_path: Path | None = None) -> None:
    path = trust_store_path or get_trust_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized_records = [
        {'path': item.path, 'sha256': item.sha256} for item in sorted(records.values(), key=lambda record: record.path)
    ]
    path.write_atomic(dumps_toml_data({'records': serialized_records}), 'w', encoding='utf-8')


def trust_local_config(local_config_path: Path, trust_store_path: Path | None = None) -> bool:
    if not local_config_path.is_file():
        return False

    canonical_path = canonical_local_config_path(local_config_path)
    current_hash = local_config_sha256(local_config_path)
    records = load_trust_records(trust_store_path)
    existing_record = records.get(canonical_path)
    already_trusted = existing_record is not None and existing_record.sha256 == current_hash

    records[canonical_path] = TrustRecord(path=canonical_path, sha256=current_hash)
    save_trust_records(records, trust_store_path)
    return already_trusted


def deny_local_config(local_config_path: Path, trust_store_path: Path | None = None) -> bool:
    canonical_path = canonical_local_config_path(local_config_path)
    records = load_trust_records(trust_store_path)
    if canonical_path not in records:
        return False

    records.pop(canonical_path, None)
    save_trust_records(records, trust_store_path)
    return True


def is_local_config_trusted(local_config_path: Path, trust_store_path: Path | None = None) -> bool:
    if not local_config_path.is_file():
        return False

    canonical_path = canonical_local_config_path(local_config_path)
    records = load_trust_records(trust_store_path)
    trusted_record = records.get(canonical_path)
    if trusted_record is None:
        return False

    current_hash = local_config_sha256(local_config_path)
    return current_hash == trusted_record.sha256


def sanitize_command_fields(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[Any, Any] = {}
        for key, item in value.items():
            if isinstance(key, str) and key.endswith('_command'):
                continue
            sanitized[key] = sanitize_command_fields(item)
        return sanitized

    if isinstance(value, list):
        return [sanitize_command_fields(item) for item in value]

    return value
