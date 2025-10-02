# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading
import time

import boto3


class RDSIAMTokenManager:
    """
    Manages AWS RDS IAM token generation and automatic refresh based on TTL.

    This class caches the generated token and automatically refreshes it when the TTL expires.
    This is useful for long-running database connections that need to periodically refresh
    their authentication tokens.

    RDS IAM tokens are valid for 15 minutes, so the default TTL is set to 10 minutes (600 seconds)
    to ensure tokens are refreshed before they expire.

    Thread-safe: Multiple threads can safely call get_token() concurrently.
    """

    def __init__(self, token_ttl_seconds=600):
        """
        Initialize the RDS IAM token manager.

        Args:
            token_ttl_seconds (int, optional): Number of seconds before refreshing the token.
                Defaults to 600 seconds (10 minutes), which provides a 5-minute safety buffer
                before the 15-minute token expiration.
        """
        self._token_ttl_seconds = token_ttl_seconds
        self._token = None
        self._token_created_at = 0
        self._lock = threading.Lock()

    def _generate_token(self, host, port, username, region, role_arn=None):
        """
        Generate an AWS RDS IAM authentication token using boto3.

        This token can be used as a password when connecting to RDS databases that have
        IAM authentication enabled. The token is valid for 15 minutes from generation.

        Args:
            host (str): The hostname of the RDS instance (e.g., 'mydb.region.rds.amazonaws.com')
            port (int): The port number of the database (e.g., 3306 for MySQL, 5432 for PostgreSQL)
            username (str): The database username to authenticate as
            region (str): The AWS region where the RDS instance is located (e.g., 'us-east-1')
            role_arn (str, optional): The ARN of an IAM role to assume before generating the token.
                This is useful for cross-account access. If not provided, uses the default
                AWS credentials/role.

        Returns:
            str: A presigned URL that can be used as a password for database authentication.
                This token expires after 15 minutes.

        Raises:
            boto3.exceptions.Boto3Error: If there are issues with AWS credentials or permissions
            botocore.exceptions.ClientError: If the RDS instance doesn't exist or IAM auth is not enabled

        Note:
            The RDS instance must have IAM authentication enabled, and the IAM user/role
            must have the 'rds-db:connect' permission for the specific database resource.
        """
        if role_arn:
            # when role_arn is defined, assume the role to generate the token
            # this can be used for cross-account access
            sts_client = boto3.client("sts")
            assumed_role = sts_client.assume_role(RoleArn=role_arn, RoleSessionName="datadog-rds-iam-auth-session")
            credentials = assumed_role["Credentials"]
            session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=region,
            )
        else:
            session = boto3.Session(region_name=region)
        client = session.client("rds")
        token = client.generate_db_auth_token(DBHostname=host, Port=port, DBUsername=username)

        return token

    def get_token(self, host, port, username, region, role_arn=None):
        """
        Get a valid RDS IAM token, generating a new one if needed.

        This method returns a cached token if:
        1. A token has been previously generated
        2. The token is still within its TTL

        Otherwise, it generates a new token.

        Args:
            host (str): The hostname of the RDS instance
            port (int): The port number of the database
            username (str): The database username to authenticate as
            region (str): The AWS region where the RDS instance is located
            role_arn (str, optional): The ARN of an IAM role to assume

        Returns:
            str: A valid RDS IAM authentication token

        Thread-safe: Can be called from multiple threads concurrently.
        """
        with self._lock:
            now = time.time()

            # Generate new token if no token exists or TTL expired
            if self._token is None or (now - self._token_created_at) >= self._token_ttl_seconds:
                self._token = self._generate_token(host, port, username, region, role_arn)
                self._token_created_at = now

            return self._token
