# (C) Datadog, Inc. 2024-present
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
    with pytest.raises(Exception, match="tls_cert.*not allowed from untrusted provider"):
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
