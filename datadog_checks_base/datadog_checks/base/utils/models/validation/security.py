# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Security validation for integration configuration parameters.

This module provides functions to validate file path configuration parameters
based on the provider trust settings. The security configuration is loaded once
in the AgentCheck class and passed via the validation context.

Security config structure (from AgentCheck.security_config):
{
    'enabled': bool,                    # integration_ignore_untrusted_file_params
    'file_paths_allowlist': list[str],  # integration_file_paths_allowlist
    'trusted_providers': list[str],     # integration_trusted_providers
    'excluded_checks': list[str],       # integration_security_excluded_checks
}
"""
from __future__ import annotations


# Type alias for security config
SecurityConfig = dict[str, bool | list[str]]


def is_provider_trusted(provider: str, security_config: SecurityConfig) -> bool:
    """
    Check if the given provider is in the trusted providers list.

    Args:
        provider: The configuration provider name (e.g., 'file', 'remote-config', 'kubernetes')
        security_config: The security configuration dict from AgentCheck.security_config

    Returns:
        True if the provider is trusted, False otherwise.
    """
    trusted = security_config.get('trusted_providers', ['file', 'remote-config'])
    return provider in trusted


def is_file_path_allowed(path: str, security_config: SecurityConfig) -> bool:
    """
    Check if the given file path is in the allowlist.

    Args:
        path: The file path to validate
        security_config: The security configuration dict from AgentCheck.security_config

    Returns:
        True if the path is allowed, False otherwise.
        An empty allowlist means all paths are allowed.
    """
    allowlist = security_config.get('file_paths_allowlist', [])
    if not allowlist:
        # Empty allowlist means all paths are allowed (backward compatibility)
        return True
    return any(path.startswith(allowed) for allowed in allowlist)


def is_check_excluded(check_name: str, security_config: SecurityConfig) -> bool:
    """
    Check if the given check is excluded from security restrictions.

    Args:
        check_name: The name of the check/integration
        security_config: The security configuration dict from AgentCheck.security_config

    Returns:
        True if the check is excluded from security restrictions, False otherwise.
    """
    excluded = security_config.get('excluded_checks', [])
    return check_name in excluded


def is_security_enabled(security_config: SecurityConfig) -> bool:
    """
    Check if file path security enforcement is enabled.

    Args:
        security_config: The security configuration dict from AgentCheck.security_config

    Returns:
        True if security is enabled, False otherwise.
    """
    return bool(security_config.get('enabled', False))


def validate_file_path(
    field_name: str,
    value: object,
    provider: str,
    check_name: str,
    security_config: SecurityConfig | None = None,
) -> object:
    """
    Validate a file path field value based on security settings.

    This function checks if a file path configuration parameter should be allowed
    based on the provider trust settings and allowlist configuration.

    Args:
        field_name: The name of the configuration field being validated
        value: The file path value to validate
        provider: The configuration provider name
        check_name: The name of the check/integration
        security_config: The security configuration dict from AgentCheck.security_config.
                        If None, validation is skipped.

    Returns:
        The original value if validation passes

    Raises:
        ValueError: If the file path is not allowed from the given provider
    """
    # If no security config provided, skip validation
    if security_config is None:
        return value

    # If value is not a string (e.g., None), skip validation
    if not isinstance(value, str):
        return value

    # If security is not enabled, allow everything
    if not is_security_enabled(security_config):
        return value

    # If check is excluded from security restrictions, allow everything
    if is_check_excluded(check_name, security_config):
        return value

    # If provider is trusted, allow everything
    if is_provider_trusted(provider, security_config):
        return value

    # If file path is in the allowlist, allow it
    if is_file_path_allowed(value, security_config):
        return value

    # Block the file path from untrusted provider
    raise ValueError(
        f"Field '{field_name}' contains file path '{value}' from untrusted provider '{provider}'. "
        f"To allow this, either add the provider to 'integration_trusted_providers' or "
        f"add the path to 'integration_file_paths_allowlist' in datadog.yaml."
    )
