# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import MagicMock, patch

import pytest

from datadog_checks.base import ConfigurationError

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_credentials():
    creds = MagicMock()
    creds.token = "test-iam-token-123"
    return creds


@pytest.fixture
def mock_google_auth(mock_credentials):
    with patch("datadog_checks.redisdb.gcp.google.auth.default", return_value=(mock_credentials, "test-project")):
        yield mock_credentials


class TestGCPIAMTokenProviderImportGuard:
    def test_raises_config_error_when_google_auth_missing(self):
        with patch("datadog_checks.redisdb.gcp.HAS_GOOGLE_AUTH", False):
            from datadog_checks.redisdb.gcp import GCPIAMTokenProvider

            with pytest.raises(ConfigurationError, match="google-auth"):
                GCPIAMTokenProvider()


class TestGCPIAMTokenProviderInit:
    def test_raises_config_error_on_missing_adc(self):
        import google.auth.exceptions

        with patch(
            "datadog_checks.redisdb.gcp.google.auth.default",
            side_effect=google.auth.exceptions.DefaultCredentialsError("no creds"),
        ):
            from datadog_checks.redisdb.gcp import GCPIAMTokenProvider

            with pytest.raises(ConfigurationError, match="application default credentials"):
                GCPIAMTokenProvider()

    def test_uses_adc_when_no_service_account(self, mock_google_auth):
        from datadog_checks.redisdb.gcp import GCPIAMTokenProvider

        provider = GCPIAMTokenProvider()
        assert provider._credentials is mock_google_auth

    def test_uses_impersonation_when_service_account_provided(self, mock_google_auth):
        mock_impersonated = MagicMock()
        mock_impersonated.token = "impersonated-token"
        with patch(
            "datadog_checks.redisdb.gcp.google.auth.impersonated_credentials.Credentials",
            return_value=mock_impersonated,
        ) as mock_impersonated_cls:
            from datadog_checks.redisdb.gcp import GCPIAMTokenProvider

            provider = GCPIAMTokenProvider(service_account="datadog@my-project.iam.gserviceaccount.com")

            mock_impersonated_cls.assert_called_once_with(
                source_credentials=mock_google_auth,
                target_principal="datadog@my-project.iam.gserviceaccount.com",
                target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            assert provider._credentials is mock_impersonated


class TestGCPIAMTokenProviderUsername:
    def test_username_always_returns_default(self, mock_google_auth):
        from datadog_checks.redisdb.gcp import GCPIAMTokenProvider

        provider = GCPIAMTokenProvider()
        assert provider.username == "default"

    def test_username_returns_default_even_with_service_account(self, mock_google_auth):
        with patch("datadog_checks.redisdb.gcp.google.auth.impersonated_credentials.Credentials"):
            from datadog_checks.redisdb.gcp import GCPIAMTokenProvider

            provider = GCPIAMTokenProvider(service_account="sa@project.iam.gserviceaccount.com")
            assert provider.username == "default"


class TestGCPIAMTokenProviderTokenLifecycle:
    def test_get_token_refreshes_on_first_call(self, mock_google_auth):
        from datadog_checks.redisdb.gcp import GCPIAMTokenProvider

        with patch("datadog_checks.redisdb.gcp.google.auth.transport.requests.Request") as mock_request_cls:
            mock_request = MagicMock()
            mock_request_cls.return_value = mock_request
            provider = GCPIAMTokenProvider()

            token = provider.get_token()

            mock_google_auth.refresh.assert_called_once_with(mock_request)
            assert token == "test-iam-token-123"

    def test_get_token_returns_cached_token_within_ttl(self, mock_google_auth):
        from datadog_checks.redisdb.gcp import GCPIAMTokenProvider

        with patch("datadog_checks.redisdb.gcp.google.auth.transport.requests.Request"):
            provider = GCPIAMTokenProvider()
            provider.get_token()
            mock_google_auth.refresh.reset_mock()

            token = provider.get_token()

            mock_google_auth.refresh.assert_not_called()
            assert token == "test-iam-token-123"

    def test_get_token_refreshes_after_ttl_expires(self, mock_google_auth):
        from datadog_checks.redisdb.gcp import TOKEN_TTL, GCPIAMTokenProvider

        with patch("datadog_checks.redisdb.gcp.google.auth.transport.requests.Request"):
            provider = GCPIAMTokenProvider()
            provider.get_token()
            mock_google_auth.refresh.reset_mock()

            provider._token_fetched_at -= TOKEN_TTL + 1

            provider.get_token()

            mock_google_auth.refresh.assert_called_once()

    def test_is_token_expired_true_before_first_fetch(self, mock_google_auth):
        from datadog_checks.redisdb.gcp import GCPIAMTokenProvider

        provider = GCPIAMTokenProvider()
        assert provider.is_token_expired() is True

    def test_is_token_expired_false_after_fresh_fetch(self, mock_google_auth):
        from datadog_checks.redisdb.gcp import GCPIAMTokenProvider

        with patch("datadog_checks.redisdb.gcp.google.auth.transport.requests.Request"):
            provider = GCPIAMTokenProvider()
            provider.get_token()
            assert provider.is_token_expired() is False

    def test_invalidate_causes_next_get_token_to_refresh(self, mock_google_auth):
        from datadog_checks.redisdb.gcp import GCPIAMTokenProvider

        with patch("datadog_checks.redisdb.gcp.google.auth.transport.requests.Request"):
            provider = GCPIAMTokenProvider()
            provider.get_token()
            mock_google_auth.refresh.reset_mock()

            provider.invalidate()
            assert provider.is_token_expired() is True

            provider.get_token()
            mock_google_auth.refresh.assert_called_once()
