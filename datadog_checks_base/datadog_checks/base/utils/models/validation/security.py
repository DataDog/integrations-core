# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Security validation for integration configuration parameters.

This module provides functions to validate file path configuration parameters
based on the provider trust settings. The security configuration is loaded once
in the AgentCheck class and passed via the validation context.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Default values for security config
DEFAULT_TRUSTED_PROVIDERS = ['file', 'remote-config']


@dataclass
class SecurityConfig:
    """
    Security configuration for integration file path validation.

    Attributes:
        check_name: The name of the check/integration.
        provider: The configuration provider name (e.g., 'file', 'remote-config', 'kubernetes').
        ignore_untrusted_file_params: Whether to ignore file params from untrusted providers
            (maps to integration_ignore_untrusted_file_params). Defaults to False.
        file_paths_allowlist: List of allowed file path prefixes. Defaults to empty list.
        trusted_providers: List of trusted configuration providers. Defaults to ['file', 'remote-config'].
        excluded_checks: List of check names excluded from security validation. Defaults to empty list.
    """

    check_name: str = ''
    provider: str = ''
    ignore_untrusted_file_params: bool = False
    file_paths_allowlist: list[str] = field(default_factory=list)
    trusted_providers: list[str] = field(default_factory=lambda: DEFAULT_TRUSTED_PROVIDERS.copy())
    excluded_checks: list[str] = field(default_factory=list)

    def is_enabled(self) -> bool:
        """Check if file path security enforcement is enabled."""
        return self.ignore_untrusted_file_params

    def is_provider_trusted(self, provider: str) -> bool:
        """
        Check if the given provider is in the trusted providers list.

        Args:
            provider: The configuration provider name (e.g., 'file', 'remote-config', 'kubernetes')

        Returns:
            True if the provider is trusted, False otherwise.
        """
        return provider in self.trusted_providers

    def is_file_path_allowed(self, path: str) -> bool:
        """
        Check if the given file path is in the allowlist.

        Args:
            path: The file path to validate

        Returns:
            True if the path is allowed, False otherwise.
            An empty allowlist means all paths are allowed.
        """
        if not self.file_paths_allowlist:
            # Empty allowlist means all paths are allowed (backward compatibility)
            return True
        return any(path.startswith(allowed) for allowed in self.file_paths_allowlist)

    def is_check_excluded(self, check_name: str) -> bool:
        """
        Check if the given check is excluded from security restrictions.

        Args:
            check_name: The name of the check/integration

        Returns:
            True if the check is excluded from security restrictions, False otherwise.
        """
        return check_name in self.excluded_checks


def validate_require_trusted_provider(
    value: object,
    security_config: SecurityConfig | None = None,
) -> bool:
    """
    Check if a value is allowed based on security settings.

    This function checks if a configuration parameter should be allowed
    based on the provider trust settings and allowlist configuration.

    Args:
        value: The value to validate
        security_config: The SecurityConfig instance containing check_name, provider,
            and security settings. If None, validation is skipped.

    Returns:
        True if the value is allowed, False if it should be blocked.
    """
    # If no security config provided, allow
    if security_config is None:
        return True

    # If value is not a string (e.g., None), allow
    if not isinstance(value, str):
        return True

    # If security is not enabled, allow
    if not security_config.is_enabled():
        return True

    # If check is excluded from security restrictions, allow
    if security_config.is_check_excluded(security_config.check_name):
        return True

    # If provider is trusted, allow
    if security_config.is_provider_trusted(security_config.provider):
        return True

    # If file path is in the allowlist, allow
    if security_config.is_file_path_allowed(value):
        return True

    # Block the value from untrusted provider
    return False
