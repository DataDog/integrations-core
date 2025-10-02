# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import mock

from datadog_checks.base.utils.db.cloud_auth import RDSIAMTokenManager


class TestRDSIAMTokenManager:
    """Test the RDSIAMTokenManager class"""

    @mock.patch.object(RDSIAMTokenManager, '_generate_token')
    def test_first_call_generates_token(self, mock_generate):
        """Test that the first call generates a new token"""
        mock_generate.return_value = 'first-token'
        manager = RDSIAMTokenManager(token_ttl_seconds=600)

        token = manager.get_token(
            host='mydb.us-east-1.rds.amazonaws.com', port=3306, username='dbuser', region='us-east-1'
        )

        assert token == 'first-token'
        mock_generate.assert_called_once_with('mydb.us-east-1.rds.amazonaws.com', 3306, 'dbuser', 'us-east-1', None)

    @mock.patch.object(RDSIAMTokenManager, '_generate_token')
    def test_cached_token_reused_within_ttl(self, mock_generate):
        """Test that cached token is reused within TTL"""
        mock_generate.return_value = 'cached-token'
        manager = RDSIAMTokenManager(token_ttl_seconds=600)

        # First call
        token1 = manager.get_token(
            host='mydb.us-east-1.rds.amazonaws.com', port=3306, username='dbuser', region='us-east-1'
        )

        # Second call (should use cached token)
        token2 = manager.get_token(
            host='mydb.us-east-1.rds.amazonaws.com', port=3306, username='dbuser', region='us-east-1'
        )

        assert token1 == token2 == 'cached-token'
        # generate_rds_iam_token should only be called once
        assert mock_generate.call_count == 1

    @mock.patch.object(RDSIAMTokenManager, '_generate_token')
    @mock.patch('datadog_checks.base.utils.db.cloud_auth.time')
    def test_token_refreshed_after_ttl(self, mock_time, mock_generate):
        """Test that token is refreshed after TTL expires"""
        mock_generate.side_effect = ['first-token', 'refreshed-token']

        # Mock time progression
        time_values = [0, 100, 700]  # 0s, 100s, 700s
        mock_time.time.side_effect = time_values

        manager = RDSIAMTokenManager(token_ttl_seconds=600)

        # First call at t=0
        token1 = manager.get_token(
            host='mydb.us-east-1.rds.amazonaws.com', port=3306, username='dbuser', region='us-east-1'
        )

        # Second call at t=100 (within TTL)
        token2 = manager.get_token(
            host='mydb.us-east-1.rds.amazonaws.com', port=3306, username='dbuser', region='us-east-1'
        )

        # Third call at t=700 (past TTL)
        token3 = manager.get_token(
            host='mydb.us-east-1.rds.amazonaws.com', port=3306, username='dbuser', region='us-east-1'
        )

        assert token1 == token2 == 'first-token'
        assert token3 == 'refreshed-token'
        assert mock_generate.call_count == 2

    @mock.patch.object(RDSIAMTokenManager, '_generate_token')
    def test_thread_safety(self, mock_generate):
        """Test that token manager is thread-safe"""
        import threading

        mock_generate.return_value = 'thread-safe-token'
        manager = RDSIAMTokenManager(token_ttl_seconds=600)

        tokens = []

        def get_token():
            token = manager.get_token(
                host='mydb.us-east-1.rds.amazonaws.com', port=3306, username='dbuser', region='us-east-1'
            )
            tokens.append(token)

        # Create multiple threads
        threads = [threading.Thread(target=get_token) for _ in range(10)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All tokens should be the same
        assert all(token == 'thread-safe-token' for token in tokens)
        # generate_rds_iam_token should only be called once despite multiple threads
        assert mock_generate.call_count == 1

    @mock.patch.object(RDSIAMTokenManager, '_generate_token')
    def test_custom_ttl(self, mock_generate):
        """Test that custom TTL is respected"""
        mock_generate.side_effect = ['first-token', 'refreshed-token']
        manager = RDSIAMTokenManager(token_ttl_seconds=300)  # 5 minutes

        # First call
        token1 = manager.get_token(
            host='mydb.us-east-1.rds.amazonaws.com', port=3306, username='dbuser', region='us-east-1'
        )

        # Simulate time passing (less than TTL)
        time.sleep(0.1)

        # Second call (should use cache)
        token2 = manager.get_token(
            host='mydb.us-east-1.rds.amazonaws.com', port=3306, username='dbuser', region='us-east-1'
        )

        assert token1 == token2
        assert mock_generate.call_count == 1
