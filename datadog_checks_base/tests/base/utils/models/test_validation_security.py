# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.models.validation.security import (
    is_provider_trusted,
    is_file_path_allowed,
    is_check_excluded,
    is_security_enabled,
    validate_file_path,
)


def make_security_config(
    enabled=False,
    file_paths_allowlist=None,
    trusted_providers=None,
    excluded_checks=None,
):
    """Helper to create a security config dict."""
    return {
        'enabled': enabled,
        'file_paths_allowlist': file_paths_allowlist or [],
        'trusted_providers': trusted_providers or ['file', 'remote-config'],
        'excluded_checks': excluded_checks or [],
    }


class TestIsProviderTrusted:
    """Tests for the is_provider_trusted function."""

    def test_default_trusted_providers(self):
        """Test that file and remote-config are trusted by default."""
        config = make_security_config()
        assert is_provider_trusted('file', config) is True
        assert is_provider_trusted('remote-config', config) is True

    def test_default_untrusted_providers(self):
        """Test that other providers are untrusted by default."""
        config = make_security_config()
        assert is_provider_trusted('kubernetes', config) is False
        assert is_provider_trusted('container', config) is False
        assert is_provider_trusted('', config) is False

    def test_custom_trusted_providers(self):
        """Test with custom trusted providers list."""
        config = make_security_config(trusted_providers=['file', 'kubernetes'])
        assert is_provider_trusted('file', config) is True
        assert is_provider_trusted('kubernetes', config) is True
        assert is_provider_trusted('remote-config', config) is False

    def test_empty_trusted_providers_uses_defaults(self):
        """Test that empty list uses empty list (not defaults)."""
        config = make_security_config(trusted_providers=[])
        assert is_provider_trusted('file', config) is False
        assert is_provider_trusted('remote-config', config) is False


class TestIsFilePathAllowed:
    """Tests for the is_file_path_allowed function."""

    def test_empty_allowlist_allows_all(self):
        """Test that empty allowlist allows all paths."""
        config = make_security_config(file_paths_allowlist=[])
        assert is_file_path_allowed('/any/path', config) is True
        assert is_file_path_allowed('/etc/passwd', config) is True

    def test_allowlist_with_matching_prefix(self):
        """Test paths matching allowlist prefixes."""
        config = make_security_config(file_paths_allowlist=['/var/log/', '/etc/datadog-agent/'])
        assert is_file_path_allowed('/var/log/syslog', config) is True
        assert is_file_path_allowed('/var/log/myapp/app.log', config) is True
        assert is_file_path_allowed('/etc/datadog-agent/conf.d/mycheck.yaml', config) is True

    def test_allowlist_blocks_non_matching_paths(self):
        """Test paths not matching allowlist are blocked."""
        config = make_security_config(file_paths_allowlist=['/var/log/', '/etc/datadog-agent/'])
        assert is_file_path_allowed('/etc/passwd', config) is False
        assert is_file_path_allowed('/home/user/secrets', config) is False
        assert is_file_path_allowed('/tmp/malicious', config) is False


class TestIsCheckExcluded:
    """Tests for the is_check_excluded function."""

    def test_empty_exclusion_list(self):
        """Test that empty exclusion list excludes nothing."""
        config = make_security_config(excluded_checks=[])
        assert is_check_excluded('disk', config) is False
        assert is_check_excluded('network', config) is False

    def test_check_in_exclusion_list(self):
        """Test that checks in exclusion list are excluded."""
        config = make_security_config(excluded_checks=['disk', 'network'])
        assert is_check_excluded('disk', config) is True
        assert is_check_excluded('network', config) is True
        assert is_check_excluded('cpu', config) is False


class TestIsSecurityEnabled:
    """Tests for the is_security_enabled function."""

    def test_security_disabled_by_default(self):
        """Test that security is disabled by default."""
        config = make_security_config(enabled=False)
        assert is_security_enabled(config) is False

    def test_security_enabled_when_true(self):
        """Test that security is enabled when config is True."""
        config = make_security_config(enabled=True)
        assert is_security_enabled(config) is True


class TestValidateFilePath:
    """Tests for the validate_file_path function."""

    def test_none_security_config_passes(self):
        """Test that None security config skips validation."""
        result = validate_file_path('log_path', '/etc/passwd', 'kubernetes', 'mycheck', None)
        assert result == '/etc/passwd'

    def test_non_string_value_passes(self):
        """Test that non-string values pass validation."""
        config = make_security_config(enabled=True)
        assert validate_file_path('field', None, 'kubernetes', 'mycheck', config) is None
        assert validate_file_path('field', 123, 'kubernetes', 'mycheck', config) == 123

    def test_security_disabled_allows_all(self):
        """Test that disabled security allows all paths."""
        config = make_security_config(enabled=False)
        result = validate_file_path('log_path', '/etc/passwd', 'kubernetes', 'mycheck', config)
        assert result == '/etc/passwd'

    def test_excluded_check_allows_all(self):
        """Test that excluded checks allow all paths."""
        config = make_security_config(
            enabled=True,
            excluded_checks=['mycheck'],
        )
        result = validate_file_path('log_path', '/etc/passwd', 'kubernetes', 'mycheck', config)
        assert result == '/etc/passwd'

    def test_trusted_provider_allows_all(self):
        """Test that trusted providers allow all paths."""
        config = make_security_config(
            enabled=True,
            trusted_providers=['file', 'remote-config'],
        )
        result = validate_file_path('log_path', '/etc/passwd', 'file', 'mycheck', config)
        assert result == '/etc/passwd'

    def test_allowlisted_path_allowed(self):
        """Test that allowlisted paths are allowed from untrusted providers."""
        config = make_security_config(
            enabled=True,
            trusted_providers=['file'],
            file_paths_allowlist=['/var/log/'],
        )
        result = validate_file_path('log_path', '/var/log/myapp.log', 'kubernetes', 'mycheck', config)
        assert result == '/var/log/myapp.log'

    def test_untrusted_provider_non_allowlisted_path_blocked(self):
        """Test that non-allowlisted paths from untrusted providers are blocked."""
        config = make_security_config(
            enabled=True,
            trusted_providers=['file'],
            file_paths_allowlist=['/var/log/'],
        )

        with pytest.raises(ValueError) as exc_info:
            validate_file_path('log_path', '/etc/passwd', 'kubernetes', 'mycheck', config)

        error_message = str(exc_info.value)
        assert 'log_path' in error_message
        assert '/etc/passwd' in error_message
        assert 'kubernetes' in error_message
        assert 'untrusted provider' in error_message

    def test_error_message_includes_guidance(self):
        """Test that error message includes guidance on how to fix."""
        config = make_security_config(
            enabled=True,
            trusted_providers=['file'],
            file_paths_allowlist=['/var/log/'],
        )

        with pytest.raises(ValueError) as exc_info:
            validate_file_path('config_file', '/secret/data', 'container', 'mycheck', config)

        error_message = str(exc_info.value)
        assert 'integration_trusted_providers' in error_message
        assert 'integration_file_paths_allowlist' in error_message


class TestSecurityConfigIntegration:
    """Integration tests simulating how AgentCheck would use this."""

    def test_full_security_flow_blocked(self):
        """Test complete flow where file path is blocked."""
        # Simulates AgentCheck.security_config
        security_config = {
            'enabled': True,
            'file_paths_allowlist': ['/opt/datadog-agent/'],
            'trusted_providers': ['file', 'remote-config'],
            'excluded_checks': ['special_check'],
        }

        # This should be blocked - untrusted provider, non-allowlisted path
        with pytest.raises(ValueError):
            validate_file_path(
                field_name='private_key_path',
                value='/etc/ssl/private/server.key',
                provider='kubernetes',
                check_name='nginx',
                security_config=security_config,
            )

    def test_full_security_flow_allowed_by_provider(self):
        """Test complete flow where file path is allowed by trusted provider."""
        security_config = {
            'enabled': True,
            'file_paths_allowlist': ['/opt/datadog-agent/'],
            'trusted_providers': ['file', 'remote-config'],
            'excluded_checks': ['special_check'],
        }

        # This should pass - trusted provider
        result = validate_file_path(
            field_name='private_key_path',
            value='/etc/ssl/private/server.key',
            provider='file',
            check_name='nginx',
            security_config=security_config,
        )
        assert result == '/etc/ssl/private/server.key'

    def test_full_security_flow_allowed_by_exclusion(self):
        """Test complete flow where check is excluded from security."""
        security_config = {
            'enabled': True,
            'file_paths_allowlist': ['/opt/datadog-agent/'],
            'trusted_providers': ['file', 'remote-config'],
            'excluded_checks': ['special_check'],
        }

        # This should pass - check is excluded
        result = validate_file_path(
            field_name='private_key_path',
            value='/etc/ssl/private/server.key',
            provider='kubernetes',
            check_name='special_check',
            security_config=security_config,
        )
        assert result == '/etc/ssl/private/server.key'

    def test_full_security_flow_allowed_by_allowlist(self):
        """Test complete flow where path is in allowlist."""
        security_config = {
            'enabled': True,
            'file_paths_allowlist': ['/opt/datadog-agent/', '/etc/ssl/'],
            'trusted_providers': ['file', 'remote-config'],
            'excluded_checks': ['special_check'],
        }

        # This should pass - path is in allowlist
        result = validate_file_path(
            field_name='private_key_path',
            value='/etc/ssl/private/server.key',
            provider='kubernetes',
            check_name='nginx',
            security_config=security_config,
        )
        assert result == '/etc/ssl/private/server.key'
