# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from psycopg import Connection


class TokenProvider(ABC):
    """
    Interface for providing a token for managed authentication.
    """

    def __init__(self, *, skew_seconds: int = 60):
        self._skew = skew_seconds
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_at: float = 0.0

    def get_token(self) -> str:
        """
        Get a token for managed authentication.
        """
        now = time.time()
        with self._lock:
            if self._token is None or now >= self._expires_at - self._skew:
                token, expires_at = self._fetch_token()
                self._token = token
                self._expires_at = float(expires_at)
            return self._token  # type: ignore[return-value]

    @abstractmethod
    def _fetch_token(self) -> tuple[str, float]:
        """
        Return (token, expires_at_epoch_seconds).
        Implementations should return the absolute expiry; if the provider
        has a fixed TTL, compute expires_at = time.time() + ttl_seconds.
        """


class AWSTokenProvider(TokenProvider):
    """
    Token provider for AWS RDS IAM authentication.
    """

    TOKEN_TTL_SECONDS = 900  # 15 minutes

    def __init__(
        self, host: str, port: int, username: str, region: str, *, role_arn: str | None = None, skew_seconds: int = 60
    ):
        super().__init__(skew_seconds=skew_seconds)
        self.host = host
        self.port = port
        self.username = username
        self.region = region
        self.role_arn = role_arn

    def _fetch_token(self) -> tuple[str, float]:
        import boto3

        if self.role_arn:
            sts_client = boto3.client("sts")
            assumed_role = sts_client.assume_role(RoleArn=self.role_arn, RoleSessionName="datadog-rds-iam-auth-session")
            credentials = assumed_role["Credentials"]
            session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=self.region,
            )
        else:
            session = boto3.Session(region_name=self.region)

        client = session.client("rds")
        token = client.generate_db_auth_token(DBHostname=self.host, Port=self.port, DBUsername=self.username)
        return token, time.time() + self.TOKEN_TTL_SECONDS


class AzureTokenProvider(TokenProvider):
    """
    Token provider for Azure Managed Identity authentication.
    """

    DEFAULT_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"

    def __init__(self, client_id: str, identity_scope: str | None = None, skew_seconds: int = 60):
        super().__init__(skew_seconds=skew_seconds)
        self.client_id = client_id
        self.identity_scope = identity_scope

    def _fetch_token(self) -> tuple[str, float]:
        from azure.identity import ManagedIdentityCredential

        credential = ManagedIdentityCredential(client_id=self.client_id)
        scope = self.identity_scope or self.DEFAULT_SCOPE
        token = credential.get_token(scope)
        return token.token, float(token.expires_on)


class TokenAwareConnection(Connection):
    """
    Connection that can be used for managed authentication.
    """

    @classmethod
    def connect(cls, *args, **kwargs):
        """
        Override the connection method to pass a refreshable token as the connection password.

        The token_provider can be passed via the 'token_provider' kwarg and will be used
        to dynamically fetch authentication tokens.
        """
        token_provider = kwargs.pop("token_provider", None)
        if token_provider:
            kwargs["password"] = token_provider.get_token()
        return super().connect(*args, **kwargs)


@dataclass(frozen=True)
class PostgresConnectionArgs:
    """
    Immutable PostgreSQL connection arguments.
    """

    username: str
    host: str | None = None
    port: int | None = None
    password: str | None = None
    token_provider: TokenProvider | None = None
    ssl_mode: str | None = "allow"
    ssl_cert: str | None = None
    ssl_root_cert: str | None = None
    ssl_key: str | None = None
    ssl_password: str | None = None
    application_name: str | None = None

    def as_kwargs(self, dbname: str) -> dict[str, Any]:
        """
        Return a dictionary of connection arguments for psycopg.
        """
        kwargs: dict[str, Any] = {
            "user": self.username,
            "dbname": dbname,
        }
        if self.application_name is not None:
            kwargs["application_name"] = self.application_name
        if self.ssl_mode is not None:
            kwargs["sslmode"] = self.ssl_mode
        if self.host:
            kwargs["host"] = self.host
        if self.password:
            kwargs["password"] = self.password
        if self.port:
            kwargs["port"] = self.port
        if self.ssl_cert:
            kwargs["sslcert"] = self.ssl_cert
        if self.ssl_root_cert:
            kwargs["sslrootcert"] = self.ssl_root_cert
        if self.ssl_key:
            kwargs["sslkey"] = self.ssl_key
        if self.ssl_password:
            kwargs["sslpassword"] = self.ssl_password
        if self.token_provider:
            kwargs["token_provider"] = self.token_provider
        return kwargs
