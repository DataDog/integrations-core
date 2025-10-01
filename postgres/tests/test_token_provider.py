# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from unittest.mock import Mock, patch

import pytest

from datadog_checks.postgres.connection_pool import AWSTokenProvider, AzureTokenProvider, TokenProvider


def test_get_token_first_call():
    """Test that get_token() calls _fetch_token() on first call."""
    provider = MockTokenProvider()
    provider._fetch_token = Mock(return_value=("test_token", time.time() + 3600))

    token = provider.get_token()

    assert token == "test_token"
    assert provider._fetch_token.call_count == 1
    assert provider._token == "test_token"


def test_get_token_cached_token_valid():
    """Test that get_token() returns cached token when still valid."""
    provider = MockTokenProvider()
    provider._token = "cached_token"
    provider._expires_at = time.time() + 3600  # Valid for 1 hour
    provider._fetch_token = Mock()

    token = provider.get_token()

    assert token == "cached_token"
    assert provider._fetch_token.call_count == 0


def test_get_token_cached_token_expired():
    """Test that get_token() fetches new token when cached token is expired."""
    provider = MockTokenProvider()
    provider._token = "old_token"
    provider._expires_at = time.time() - 1  # Expired
    provider._fetch_token = Mock(return_value=("new_token", time.time() + 3600))

    token = provider.get_token()

    assert token == "new_token"
    assert provider._fetch_token.call_count == 1
    assert provider._token == "new_token"


def test_get_token_skew_handling():
    """Test that get_token() respects skew_seconds for token refresh."""
    provider = MockTokenProvider(skew_seconds=60)
    provider._token = "cached_token"
    # Token expires in 30 seconds, but skew is 60 seconds, so should refresh
    provider._expires_at = time.time() + 30
    provider._fetch_token = Mock(return_value=("new_token", time.time() + 3600))

    token = provider.get_token()

    assert token == "new_token"
    assert provider._fetch_token.call_count == 1


def test_thread_safety():
    """Test that TokenProvider is thread-safe."""
    import threading

    provider = MockTokenProvider()
    provider._fetch_token = Mock(return_value=("test_token", time.time() + 3600))

    results = []

    def get_token():
        results.append(provider.get_token())

    # Start multiple threads
    threads = [threading.Thread(target=get_token) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # All threads should get the same token
    assert all(token == "test_token" for token in results)
    # _fetch_token should only be called
    assert provider._fetch_token.call_count == 1


def test_aws_token_provider_initialization():
    """Test AWSTokenProvider initialization."""
    provider = AWSTokenProvider(
        host="test-host",
        port=5432,
        username="testuser",
        region="us-east-1",
        role_arn="arn:aws:iam::123456789012:role/test-role",
    )

    assert provider.host == "test-host"
    assert provider.port == 5432
    assert provider.username == "testuser"
    assert provider.region == "us-east-1"
    assert provider.role_arn == "arn:aws:iam::123456789012:role/test-role"
    assert provider.TOKEN_TTL_SECONDS == 900


def test_aws_token_provider_initialization_without_role_arn():
    """Test AWSTokenProvider initialization without role_arn."""
    provider = AWSTokenProvider(host="test-host", port=5432, username="testuser", region="us-east-1")

    assert provider.role_arn is None


@patch('datadog_checks.postgres.connection_pool.time.time')
@patch('datadog_checks.postgres.aws.generate_rds_iam_token')
def test_aws_fetch_token_with_role_arn(mock_generate_token, mock_time):
    """Test AWS token fetching with role_arn."""
    mock_time.return_value = 1000.0
    mock_generate_token.return_value = "aws_token_123"

    provider = AWSTokenProvider(
        host="test-host",
        port=5432,
        username="testuser",
        region="us-east-1",
        role_arn="arn:aws:iam::123456789012:role/test-role",
    )

    token, expires_at = provider._fetch_token()

    assert token == "aws_token_123"
    assert expires_at == 1900.0  # 1000.0 + 900 (TOKEN_TTL_SECONDS)
    mock_generate_token.assert_called_once_with(
        host="test-host",
        port=5432,
        username="testuser",
        region="us-east-1",
        role_arn="arn:aws:iam::123456789012:role/test-role",
    )


@patch('datadog_checks.postgres.connection_pool.time.time')
@patch('datadog_checks.postgres.aws.generate_rds_iam_token')
def test_aws_fetch_token_without_role_arn(mock_generate_token, mock_time):
    """Test AWS token fetching without role_arn."""
    mock_time.return_value = 1000.0
    mock_generate_token.return_value = "aws_token_456"

    provider = AWSTokenProvider(host="test-host", port=5432, username="testuser", region="us-east-1")

    token, expires_at = provider._fetch_token()

    assert token == "aws_token_456"
    assert expires_at == 1900.0
    mock_generate_token.assert_called_once_with(
        host="test-host", port=5432, username="testuser", region="us-east-1", role_arn=None
    )


def test_aws_token_provider_integration():
    """Test AWSTokenProvider integration with get_token()."""
    with patch('datadog_checks.postgres.aws.generate_rds_iam_token') as mock_generate:
        mock_generate.return_value = "integration_token"

        provider = AWSTokenProvider(host="test-host", port=5432, username="testuser", region="us-east-1")

        # First call should fetch token
        token1 = provider.get_token()
        assert token1 == "integration_token"
        assert mock_generate.call_count == 1

        # Second call should use cached token
        token2 = provider.get_token()
        assert token2 == "integration_token"
        assert mock_generate.call_count == 1


def test_azure_token_provider_initialization():
    """Test AzureTokenProvider initialization."""
    provider = AzureTokenProvider(client_id="test-client-id", identity_scope="https://test.scope/.default")

    assert provider.client_id == "test-client-id"
    assert provider.identity_scope == "https://test.scope/.default"


def test_azure_token_provider_initialization_without_scope():
    """Test AzureTokenProvider initialization without identity_scope."""
    provider = AzureTokenProvider(client_id="test-client-id")

    assert provider.identity_scope is None


@patch('datadog_checks.postgres.azure.ManagedIdentityCredential')
def test_azure_fetch_token_with_scope(mock_credential_class):
    """Test Azure token fetching with custom scope."""
    mock_token = Mock()
    mock_token.token = "azure_token_123"
    mock_token.expires_at = 1900.0

    mock_credential = Mock()
    mock_credential.get_token.return_value = mock_token
    mock_credential_class.return_value = mock_credential

    provider = AzureTokenProvider(client_id="test-client-id", identity_scope="https://custom.scope/.default")

    token, expires_at = provider._fetch_token()

    assert token == "azure_token_123"
    assert expires_at == 1900.0
    mock_credential_class.assert_called_once_with(client_id="test-client-id")
    mock_credential.get_token.assert_called_once_with("https://custom.scope/.default")


@patch('datadog_checks.postgres.azure.ManagedIdentityCredential')
def test_azure_fetch_token_without_scope(mock_credential_class):
    """Test Azure token fetching without custom scope (uses default)."""
    mock_token = Mock()
    mock_token.token = "azure_token_456"
    mock_token.expires_at = 2000.0

    mock_credential = Mock()
    mock_credential.get_token.return_value = mock_token
    mock_credential_class.return_value = mock_credential

    provider = AzureTokenProvider(client_id="test-client-id")

    token, expires_at = provider._fetch_token()

    assert token == "azure_token_456"
    assert expires_at == 2000.0
    mock_credential_class.assert_called_once_with(client_id="test-client-id")
    mock_credential.get_token.assert_called_once_with("https://ossrdbms-aad.database.windows.net/.default")


def test_azure_token_provider_integration():
    """Test AzureTokenProvider integration with get_token()."""
    with patch('datadog_checks.postgres.azure.ManagedIdentityCredential') as mock_credential_class:
        mock_token = Mock()
        mock_token.token = "integration_azure_token"
        mock_token.expires_at = time.time() + 3600

        mock_credential = Mock()
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential

        provider = AzureTokenProvider(client_id="test-client-id")

        # First call should fetch token
        token1 = provider.get_token()
        assert token1 == "integration_azure_token"
        assert mock_credential.get_token.call_count == 1

        # Second call should use cached token
        token2 = provider.get_token()
        assert token2 == "integration_azure_token"
        assert mock_credential.get_token.call_count == 1


class MockTokenProvider(TokenProvider):
    """Mock implementation of TokenProvider for testing."""

    def _fetch_token(self):
        return "mock_token", time.time() + 3600
