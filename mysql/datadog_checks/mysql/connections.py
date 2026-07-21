# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import threading
import time
from abc import ABC, abstractmethod
from contextlib import closing, contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

import pymysql

from datadog_checks.mysql.cursor import CommenterCursor


class TokenProvider(ABC):
    """Provides a cached, self-refreshing token for managed authentication."""

    def __init__(self, *, skew_seconds: int = 60) -> None:
        self._skew = skew_seconds
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_at: float = 0.0

    def get_token(self) -> str:
        now = time.time()
        with self._lock:
            if self._token is None or now >= self._expires_at - self._skew:
                token, expires_at = self._fetch_token()
                self._token = token
                self._expires_at = float(expires_at)
            return self._token

    @abstractmethod
    def _fetch_token(self) -> tuple[str, float]:
        """Return (token, expires_at_epoch_seconds)."""


class AWSTokenProvider(TokenProvider):
    """Token provider for AWS RDS IAM authentication."""

    TOKEN_TTL_SECONDS = 900  # 15 minutes

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        region: str,
        *,
        role_arn: str | None = None,
        skew_seconds: int = 60,
    ) -> None:
        super().__init__(skew_seconds=skew_seconds)
        self.host = host
        self.port = port
        self.username = username
        self.region = region
        self.role_arn = role_arn

    def _fetch_token(self) -> tuple[str, float]:
        from .aws import generate_rds_iam_token

        token = generate_rds_iam_token(
            host=self.host,
            port=self.port,
            username=self.username,
            region=self.region,
            role_arn=self.role_arn,
        )
        return token, time.time() + self.TOKEN_TTL_SECONDS


@dataclass(frozen=True)
class MySQLConnectionArgs:
    """Immutable MySQL connection arguments. Produces the pymysql.connect() kwargs on demand."""

    host: str = ''
    port: int = 0
    user: str = ''
    password: str = ''
    unix_socket: str = ''
    defaults_file: str = ''
    ssl: dict | None = None
    connect_timeout: int = 10
    read_timeout: int | None = None
    charset: str | None = None
    token_provider: TokenProvider | None = None

    def as_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            'ssl': dict(self.ssl) if self.ssl else None,
            'connect_timeout': self.connect_timeout,
            'read_timeout': self.read_timeout,
            'autocommit': True,
        }
        if self.charset:
            kwargs['charset'] = self.charset

        if self.defaults_file != '':
            kwargs['read_default_file'] = self.defaults_file
            return kwargs

        password = self.token_provider.get_token() if self.token_provider else self.password
        kwargs['user'] = self.user
        kwargs['password'] = password

        if self.unix_socket != '':
            kwargs['unix_socket'] = self.unix_socket
        else:
            kwargs['host'] = self.host

        if self.port:
            kwargs['port'] = self.port
        return kwargs


class MySQLConnectionManager:
    """
    Single shared authority for MySQL connections.

    pymysql connections are not thread-safe, and each consumer (the main check and every
    DBMAsyncJob) runs on its own thread, so the manager vends exactly one connection per
    consumer key. Each connection is liveness-checked on acquisition and transparently
    rebuilt with a fresh managed-auth token when it is dead.
    """

    def __init__(self, check: Any, connection_args: MySQLConnectionArgs) -> None:
        self._check = check
        self._log = check.log
        self._args = connection_args
        self._lock = threading.Lock()
        self._connections: dict[str, pymysql.connections.Connection] = {}

    @contextmanager
    def get_connection(self, key: str) -> Iterator[pymysql.connections.Connection]:
        """Yield a live connection for the given consumer key, creating or rebuilding it as needed."""
        conn = self._get_or_create(key)
        yield conn

    def _get_or_create(self, key: str) -> pymysql.connections.Connection:
        with self._lock:
            conn = self._connections.get(key)
            if conn is not None:
                if self._is_alive(conn):
                    return conn
                self._close(key)
            conn = self._create()
            self._connections[key] = conn
            return conn

    def _is_alive(self, conn: pymysql.connections.Connection) -> bool:
        try:
            conn.ping(reconnect=False)
            return True
        except Exception:
            return False

    def _create(self) -> pymysql.connections.Connection:
        kwargs = self._args.as_kwargs()
        try:
            db = pymysql.connect(**kwargs)
        except Exception as e:
            self._emit_error(e)
            raise
        try:
            self._apply_session_variables(db)
        except Exception as e:
            db.close()
            self._emit_error(e)
            raise
        self._log.debug("Connected to MySQL")
        return db

    def _apply_session_variables(self, db: pymysql.connections.Connection) -> None:
        with closing(db.cursor(CommenterCursor)) as cursor:
            # PyMySQL only sets autocommit if it receives a different value from the server, and there are cases
            # where the server does not report a correct value, so set it explicitly.
            cursor.execute("SET AUTOCOMMIT=1")
            # Lower the lock wait timeout to avoid deadlocks on metadata locks. The server default is a year.
            cursor.execute("SET LOCK_WAIT_TIMEOUT=5")

    def close(self, key: str) -> None:
        with self._lock:
            self._close(key)

    def close_all(self) -> None:
        with self._lock:
            for key in list(self._connections):
                self._close(key)

    def _close(self, key: str) -> None:
        conn = self._connections.pop(key, None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                self._log.debug("Failed to close db connection for %s", key, exc_info=True)

    def _emit_error(self, error: Exception) -> None:
        try:
            self._check.count(
                "dd.mysql.db.error",
                1,
                tags=self._check.tag_manager.get_tags()
                + ["error:{}".format(type(error).__name__)]
                + self._check._get_debug_tags(),
                hostname=self._check.reported_hostname,
            )
        except Exception:
            self._log.debug("Failed to emit dd.mysql.db.error", exc_info=True)
