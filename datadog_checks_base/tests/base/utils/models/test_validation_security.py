# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.validation.security import SecurityConfig, validate_require_trusted_provider


def test_allowed_when_no_config():
    """Returns True when security config is None."""
    assert validate_require_trusted_provider('/etc/passwd', 'kubernetes', 'mycheck', None) is True


def test_allowed_when_disabled():
    """Returns True when security is disabled (default)."""
    config = SecurityConfig()
    assert validate_require_trusted_provider('/etc/passwd', 'kubernetes', 'mycheck', config) is True


def test_allowed_for_trusted_provider():
    """Returns True for trusted providers."""
    config = SecurityConfig(ignore_untrusted_file_params=True)
    assert validate_require_trusted_provider('/etc/passwd', 'file', 'mycheck', config) is True


def test_allowed_for_excluded_check():
    """Returns True for excluded checks."""
    config = SecurityConfig(ignore_untrusted_file_params=True, excluded_checks=['mycheck'])
    assert validate_require_trusted_provider('/etc/passwd', 'kubernetes', 'mycheck', config) is True


def test_allowed_for_allowlisted_path():
    """Returns True for allowlisted paths from untrusted providers."""
    config = SecurityConfig(
        ignore_untrusted_file_params=True,
        trusted_providers=['file'],
        file_paths_allowlist=['/var/log/'],
    )
    assert validate_require_trusted_provider('/var/log/app.log', 'kubernetes', 'mycheck', config) is True


def test_blocked_for_untrusted_provider():
    """Returns False for non-allowlisted paths from untrusted providers."""
    config = SecurityConfig(
        ignore_untrusted_file_params=True,
        trusted_providers=['file'],
        file_paths_allowlist=['/var/log/'],
    )
    assert validate_require_trusted_provider('/etc/passwd', 'kubernetes', 'mycheck', config) is False


def test_allowed_for_non_string_values():
    """Returns True for non-string values (None, dict, etc.)."""
    config = SecurityConfig(ignore_untrusted_file_params=True, trusted_providers=[])
    assert validate_require_trusted_provider(None, 'kubernetes', 'mycheck', config) is True
    assert validate_require_trusted_provider({'key': 'value'}, 'kubernetes', 'mycheck', config) is True
