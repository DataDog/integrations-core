# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Tests for security validation of configuration fields marked with `require_trusted_provider: true`.
"""

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.models.validation.security import SecurityConfig

from .config_models import ConfigMixin


class Check(AgentCheck, ConfigMixin):
    """Test check that allows injecting security configuration."""

    def __init__(self, name, init_config, instances, security_config=None):
        super().__init__(name, init_config, instances)
        self._injected_security_config = security_config

    @property
    def security_config(self):
        if self._injected_security_config is not None:
            return self._injected_security_config
        return super().security_config

    def check(self, _):
        pass


def test_secure_field_blocked_from_untrusted_provider(dd_run_check):
    """Secure fields from untrusted providers are blocked."""
    # Arrange
    instance = {'tls_cert': '/etc/ssl/cert.pem'}
    security_config = SecurityConfig(check_name='test', provider='kubernetes', ignore_untrusted_file_params=True)
    check = Check('test', {}, [instance], security_config=security_config)
    check.check_id = 'test:123'

    # Act & Assert
    with pytest.raises(Exception, match="(?s)ConfigurationError.*tls_cert.*not allowed from untrusted provider"):
        dd_run_check(check)


def test_secure_field_allowed_from_trusted_provider(dd_run_check):
    """Secure fields from trusted providers are allowed."""
    # Arrange
    instance = {'tls_cert': '/etc/ssl/cert.pem'}
    security_config = SecurityConfig(check_name='test', provider='file', ignore_untrusted_file_params=True)
    check = Check('test', {}, [instance], security_config=security_config)
    check.check_id = 'test:123'

    # Act
    dd_run_check(check)

    # Assert
    assert check.config.tls_cert == '/etc/ssl/cert.pem'


def test_secure_field_allowed_when_security_disabled(dd_run_check):
    """Secure fields are allowed from any provider when security is disabled."""
    # Arrange
    instance = {'tls_cert': '/etc/ssl/cert.pem'}
    security_config = SecurityConfig(check_name='test', provider='kubernetes', ignore_untrusted_file_params=False)
    check = Check('test', {}, [instance], security_config=security_config)
    check.check_id = 'test:123'

    # Act
    dd_run_check(check)

    # Assert
    assert check.config.tls_cert == '/etc/ssl/cert.pem'


def test_non_secure_field_allowed_from_any_provider(dd_run_check):
    """Non-secure fields are allowed regardless of provider."""
    # Arrange
    instance = {'timeout': 30}
    security_config = SecurityConfig(check_name='test', provider='kubernetes', ignore_untrusted_file_params=True)
    check = Check('test', {}, [instance], security_config=security_config)
    check.check_id = 'test:123'

    # Act
    dd_run_check(check)

    # Assert
    assert check.config.timeout == 30


def test_fallback_global_secure_field_blocked_from_untrusted_provider(dd_run_check):
    """Fields in GLOBAL_SECURE_FIELDS but not in the model's SECURE_FIELD_NAMES are caught by the fallback."""
    instance = {'tls_private_key': '/etc/ssl/key.pem'}
    security_config = SecurityConfig(check_name='test', provider='kubernetes', ignore_untrusted_file_params=True)
    check = Check('test', {}, [instance], security_config=security_config)
    check.check_id = 'test:123'

    with pytest.raises(Exception, match="(?s)ConfigurationError.*tls_private_key.*not allowed from untrusted provider"):
        dd_run_check(check)


def test_secure_field_allowed_via_allowlist(dd_run_check):
    """Secure fields with paths in the allowlist are allowed."""
    instance = {'tls_cert': '/etc/ssl/cert.pem'}
    security_config = SecurityConfig(
        check_name='test', provider='kubernetes', ignore_untrusted_file_params=True, file_paths_allowlist=['/etc/ssl']
    )
    check = Check('test', {}, [instance], security_config=security_config)
    check.check_id = 'test:123'

    dd_run_check(check)

    assert check.config.tls_cert == '/etc/ssl/cert.pem'


def test_auth_token_blocked_from_untrusted_provider(dd_run_check):
    """Object-typed secure fields like auth_token are blocked from untrusted providers."""
    instance = {
        'auth_token': {
            'reader': {'type': 'file', 'path': '/etc/secret'},
            'writer': {'type': 'header', 'name': 'Authorization'},
        }
    }
    security_config = SecurityConfig(check_name='test', provider='kubernetes', ignore_untrusted_file_params=True)
    check = Check('test', {}, [instance], security_config=security_config)
    check.check_id = 'test:123'

    with pytest.raises(Exception, match="(?s)ConfigurationError.*auth_token.*not allowed from untrusted provider"):
        dd_run_check(check)


def test_auth_token_allowed_via_allowlist(dd_run_check):
    """Object-typed secure fields are allowed when all nested file paths are in the allowlist."""
    instance = {
        'auth_token': {
            'reader': {'type': 'file', 'path': '/etc/secret'},
            'writer': {'type': 'header', 'name': 'Authorization'},
        }
    }
    security_config = SecurityConfig(
        check_name='test', provider='kubernetes', ignore_untrusted_file_params=True, file_paths_allowlist=['/etc']
    )
    check = Check('test', {}, [instance], security_config=security_config)
    check.check_id = 'test:123'

    dd_run_check(check)

    assert check.config.auth_token.reader['path'] == '/etc/secret'


def test_auth_token_blocked_when_path_not_in_allowlist(dd_run_check):
    """auth_token with a file reader is blocked when the path is not covered by the allowlist."""
    instance = {
        'auth_token': {
            'reader': {'type': 'file', 'path': '/var/secrets/token'},
            'writer': {'type': 'header', 'name': 'Authorization'},
        }
    }
    security_config = SecurityConfig(
        check_name='test', provider='kubernetes', ignore_untrusted_file_params=True, file_paths_allowlist=['/etc']
    )
    check = Check('test', {}, [instance], security_config=security_config)
    check.check_id = 'test:123'

    with pytest.raises(Exception, match="(?s)ConfigurationError.*auth_token.*not allowed from untrusted provider"):
        dd_run_check(check)


def test_auth_token_private_key_path_blocked_from_untrusted_provider(dd_run_check):
    """auth_token reader.private_key_path is also checked against the allowlist."""
    instance = {
        'auth_token': {
            'reader': {'type': 'file', 'path': '/etc/secret', 'private_key_path': '/var/keys/key.pem'},
            'writer': {'type': 'header', 'name': 'Authorization'},
        }
    }
    security_config = SecurityConfig(
        check_name='test', provider='kubernetes', ignore_untrusted_file_params=True, file_paths_allowlist=['/etc']
    )
    check = Check('test', {}, [instance], security_config=security_config)
    check.check_id = 'test:123'

    with pytest.raises(Exception, match="(?s)ConfigurationError.*auth_token.*not allowed from untrusted provider"):
        dd_run_check(check)


def test_auth_token_private_key_path_allowed_via_allowlist(dd_run_check):
    """auth_token is allowed when both reader.path and reader.private_key_path are in the allowlist."""
    instance = {
        'auth_token': {
            'reader': {'type': 'file', 'path': '/etc/secret', 'private_key_path': '/etc/keys/key.pem'},
            'writer': {'type': 'header', 'name': 'Authorization'},
        }
    }
    security_config = SecurityConfig(
        check_name='test', provider='kubernetes', ignore_untrusted_file_params=True, file_paths_allowlist=['/etc']
    )
    check = Check('test', {}, [instance], security_config=security_config)
    check.check_id = 'test:123'

    dd_run_check(check)

    assert check.config.auth_token.reader['private_key_path'] == '/etc/keys/key.pem'


def test_auth_token_oauth_allowed_from_untrusted_provider(dd_run_check):
    """auth_token with a non-file reader type is allowed since it has no local file paths."""
    instance = {
        'auth_token': {
            'reader': {'type': 'oauth', 'url': 'https://example.com/token', 'client_id': 'id', 'client_secret': 's'},
            'writer': {'type': 'header', 'name': 'Authorization'},
        }
    }
    security_config = SecurityConfig(check_name='test', provider='kubernetes', ignore_untrusted_file_params=True)
    check = Check('test', {}, [instance], security_config=security_config)
    check.check_id = 'test:123'

    dd_run_check(check)

    assert check.config.auth_token.reader['type'] == 'oauth'


def test_secure_field_allowed_when_check_excluded(dd_run_check):
    """Secure fields are allowed when the check is in the excluded list."""
    instance = {'tls_cert': '/etc/ssl/cert.pem'}
    security_config = SecurityConfig(
        check_name='test', provider='kubernetes', ignore_untrusted_file_params=True, excluded_checks=['test']
    )
    check = Check('test', {}, [instance], security_config=security_config)
    check.check_id = 'test:123'

    dd_run_check(check)

    assert check.config.tls_cert == '/etc/ssl/cert.pem'
