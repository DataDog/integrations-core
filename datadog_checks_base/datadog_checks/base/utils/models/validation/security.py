# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
from dataclasses import dataclass, field

DEFAULT_TRUSTED_PROVIDERS: tuple[str, ...] = ('file', 'remote-config')


@dataclass
class SecurityConfig:
    """Security configuration for integration file path validation."""

    check_name: str = ''
    provider: str = ''
    ignore_untrusted_file_params: bool = False
    file_paths_allowlist: list[str] = field(default_factory=list)
    trusted_providers: list[str] = field(default_factory=lambda: list(DEFAULT_TRUSTED_PROVIDERS))
    excluded_checks: list[str] = field(default_factory=list)

    def is_enabled(self) -> bool:
        """Return whether file path security enforcement is enabled."""
        return self.ignore_untrusted_file_params

    def is_provider_trusted(self, provider: str) -> bool:
        """Return whether the given provider is in the trusted providers list."""
        return provider in self.trusted_providers

    def is_file_path_allowed(self, path: str) -> bool:
        """Return whether the resolved path falls under any allowed prefix directory."""
        resolved = os.path.realpath(path)
        return any(
            resolved == os.path.realpath(allowed) or resolved.startswith(os.path.realpath(allowed) + os.sep)
            for allowed in self.file_paths_allowlist
        )

    def is_check_excluded(self, check_name: str) -> bool:
        """Return whether the given check is excluded from security restrictions."""
        return check_name in self.excluded_checks


def _get_auth_token_file_paths(value: dict) -> list[str]:
    """Extract file paths from an auth_token object when reader.type is 'file'."""
    reader = value.get('reader')
    if not isinstance(reader, dict):
        return []
    if reader.get('type') != 'file':
        return []
    paths: list[str] = []
    for key in ('path', 'private_key_path'):
        path = reader.get(key)
        if isinstance(path, str):
            paths.append(path)
    return paths


def validate_require_trusted_provider(
    field_name: str,
    value: object,
    security_config: SecurityConfig | None = None,
) -> bool:
    """Return True if the value is allowed based on security settings, False if it should be blocked."""
    if security_config is None:
        return True
    if not security_config.is_enabled():
        return True
    if security_config.is_check_excluded(security_config.check_name):
        return True
    if security_config.is_provider_trusted(security_config.provider):
        return True
    if isinstance(value, str):
        return security_config.is_file_path_allowed(value)
    # auth_token is the only non-string field with require_trusted_provider;
    # validate its reader.path when reader.type is 'file'
    if field_name == 'auth_token' and isinstance(value, dict):
        file_paths = _get_auth_token_file_paths(value)
        if file_paths:
            return all(security_config.is_file_path_allowed(p) for p in file_paths)
        return True
    return False


def check_field_trusted_provider(
    field_name: str,
    value: object,
    security_config: SecurityConfig | None,
) -> None:
    """Raise ValueError if the field value is not allowed from an untrusted provider."""
    if not validate_require_trusted_provider(field_name, value, security_config):
        provider = security_config.provider
        raise ValueError(f"Field '{field_name}' is not allowed from untrusted provider '{provider}'")
