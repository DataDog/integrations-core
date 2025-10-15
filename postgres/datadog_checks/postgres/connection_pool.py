# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union

from psycopg import Connection
from psycopg_pool import ConnectionPool

from .cursor import CommenterCursor, SQLASCIITextLoader


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
    def _fetch_token(self) -> Tuple[str, float]:
        """
        Return (token, expires_at_epoch_seconds).
        Implementations should return the absolute expiry; if the provider
        has a fixed TTL, compute expires_at = time.time() + ttl_seconds.
        """


class AWSTokenProvider(TokenProvider):
    """
    Token provider for AWS IAM authentication.
    """

    TOKEN_TTL_SECONDS = 900  # 15 minutes

    def __init__(
        self, host: str, port: int, username: str, region: str, *, role_arn: str = None, skew_seconds: int = 60
    ):
        super().__init__(skew_seconds=skew_seconds)
        self.host = host
        self.port = port
        self.username = username
        self.region = region
        self.role_arn = role_arn

    def _fetch_token(self) -> Tuple[str, float]:
        # Import aws only when this method is called
        from .aws import generate_rds_iam_token

        token = generate_rds_iam_token(
            host=self.host, port=self.port, username=self.username, region=self.region, role_arn=self.role_arn
        )
        return token, time.time() + self.TOKEN_TTL_SECONDS


class AzureTokenProvider(TokenProvider):
    """
    Token provider for Azure Managed Identity.
    """

    def __init__(self, client_id: str, identity_scope: str = None, skew_seconds: int = 60):
        super().__init__(skew_seconds=skew_seconds)
        self.client_id = client_id
        self.identity_scope = identity_scope

    def _fetch_token(self) -> Tuple[str, float]:
        # Import azure only when this method is called
        from .azure import generate_managed_identity_token

        token = generate_managed_identity_token(client_id=self.client_id, identity_scope=self.identity_scope)
        return token.token, float(token.expires_at)


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

    application_name: str
    username: str
    host: Optional[str] = None
    port: Optional[int] = None
    password: Optional[str] = None
    token_provider: Optional[TokenProvider] = None
    ssl_mode: Optional[str] = "allow"
    ssl_cert: Optional[str] = None
    ssl_root_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_password: Optional[str] = None

    def as_kwargs(self, dbname: str) -> Dict[str, Union[str, int]]:
        """
        Return a dictionary of connection arguments for psycopg.

        Args:
            dbname (str): The database name to connect to.

        Returns:
            Dict[str, Union[str, int]]: Connection arguments dictionary with string and integer values.
        """
        kwargs = {
            "application_name": self.application_name,
            "user": self.username,
            "dbname": dbname,
            "sslmode": self.ssl_mode,
        }
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
        return kwargs


class LRUConnectionPoolManager:
    """
    Manages a fixed-size set of psycopg3 ConnectionPools, one per database name (dbname),
    evicting the least recently used pool when the limit is exceeded.

    Each dbname is assigned its own psycopg_pool.ConnectionPool instance. Only one pool
    is maintained per dbname, and the total number of active pools is capped by `max_db`.

    Pools are reused across calls, and usage is tracked to enforce LRU eviction. When a
    new dbname is accessed beyond the pool limit, the least recently used pool is closed
    and removed to make room.

    Optionally supports runtime inspection of pool stats and last-used times.
    """

    def __init__(
        self,
        max_db: int,
        base_conn_args: PostgresConnectionArgs,
        pool_config: Optional[Dict[str, Any]] = None,
        statement_timeout: Optional[int] = None,  # milliseconds
        sqlascii_encodings: Optional[list[str]] = None,
        token_provider: Optional[TokenProvider] = None,
    ) -> None:
        """
        Initialize the pool manager.

        Args:
            max_db (int): Maximum number of unique dbname pools to maintain.
            base_conn_args (PostgresConnectionArgs): Common connection parameters.
            pool_config (dict, optional): Additional ConnectionPool settings (min_size, max_size, etc).
            statement_timeout (int, optional): Statement timeout in milliseconds.
            sqlascii_encodings (list[str], optional): List of encodings to handle for SQLASCII text.
            token_provider (TokenProvider, optional): Token provider for managed authentication.
        """
        self.max_db = max_db
        self.base_conn_args = base_conn_args
        self.statement_timeout = statement_timeout
        self.sqlascii_encodings = sqlascii_encodings
        self.token_provider = token_provider

        self.pool_config = {
            **(pool_config or {}),
            "min_size": 0,
            "max_size": 2,
            "open": True,
        }

        self.lock = threading.Lock()
        self.pools: OrderedDict[str, Tuple[ConnectionPool, float, bool]] = OrderedDict()
        self._closed = False

    def _configure_connection(self, conn: Connection) -> None:
        conn.autocommit = True

        if conn.info.encoding.lower() in ['ascii', 'sqlascii', 'sql_ascii']:
            text_loader = SQLASCIITextLoader
            text_loader.encodings = self.sqlascii_encodings
            for typ in ["text", "varchar", "name", "regclass"]:
                conn.adapters.register_loader(typ, text_loader)

        conn.cursor_factory = CommenterCursor

        with conn.cursor() as cur:
            if self.statement_timeout is not None:
                cur.execute("SET statement_timeout = %s", (self.statement_timeout,))

    def _create_pool(self, dbname: str) -> ConnectionPool:
        """
        Create a new ConnectionPool for a given dbname using a kwargs.

        Args:
            dbname (str): The target database name.

        Returns:
            ConnectionPool: A new pool instance configured for the dbname.
        """
        kwargs = self.base_conn_args.as_kwargs(dbname=dbname)

        # Pass the token_provider as a kwarg so it's available to TokenAwareConnection.connect()
        if self.token_provider:
            kwargs["token_provider"] = self.token_provider

        return ConnectionPool(
            kwargs=kwargs,
            configure=self._configure_connection,
            connection_class=TokenAwareConnection,
            **self.pool_config,
        )

    def get_connection(self, dbname: str, persistent: bool = False):
        """
        Context-managed access to a single connection from the pool associated with the given dbname.

        Ensures that the connection is returned to its pool after use. Returns the context manager
        from psycopg_pool.ConnectionPool.connection().

        Usage:
            with manager.get_connection("mydb") as conn:
                with conn.cursor() as cur:
                    cur.execute(...)

        Args:
            dbname (str): The database name to get a connection for.
            persistent (bool): Whether the underlying pool should be marked as persistent.

        Returns:
            Context manager yielding a psycopg.Connection.

        Raises:
            RuntimeError: If the pool manager has been closed.
        """
        with self.lock:
            if self._closed:
                raise RuntimeError("Pool manager is closed and cannot get connection")

            now = time.monotonic()

            # Get or create pool
            if dbname in self.pools:
                pool, _, was_persistent = self.pools.pop(dbname)
                self.pools[dbname] = (pool, now, was_persistent or persistent)
            else:
                # Create new pool, potentially evicting old ones
                if len(self.pools) >= self.max_db:
                    # Try to evict a non-persistent pool first
                    for evict_dbname in list(self.pools.keys()):
                        _, _, is_persistent = self.pools[evict_dbname]
                        if not is_persistent:
                            old_pool, _, _ = self.pools.pop(evict_dbname)
                            old_pool.close()
                            break
                    else:
                        # All remaining are persistent, evict true LRU
                        evict_dbname, (old_pool, _, _) = self.pools.popitem(last=False)
                        old_pool.close()

                pool = self._create_pool(dbname)
                self.pools[dbname] = (pool, now, persistent)

            # Return the pool's context manager directly
            return pool.connection()

    def get_pool_stats(self, dbname: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve runtime statistics and metadata for the ConnectionPool associated with the given dbname.

        Includes:
            - used: Connections currently in use
            - available: Idle connections ready for use
            - total: Total connections managed by the pool
            - waiters: Threads waiting for a connection
            - last_used: Monotonic timestamp of last access
            - persistent: Whether the pool is marked as persistent

        Args:
            dbname (str): The database name to fetch stats for.

        Returns:
            Optional[Dict[str, Any]]: Dictionary of pool stats and metadata, or None if the pool does not exist.
        """
        with self.lock:
            entry = self.pools.get(dbname)
            if not entry:
                return None
            pool, last_used, persistent = entry
            stats = pool.get_stats()
            return {
                **stats,
                "last_used": last_used,
                "persistent": persistent,
            }

    def close_all(self) -> None:
        """
        Gracefully close all active pools including persistent ones and release all underlying connections.

        This clears the pool manager state and prevents new pools from being created.
        Should be called during shutdown or cleanup.
        """
        with self.lock:
            self._closed = True
            for pool, _, _ in self.pools.values():
                pool.close()
            self.pools.clear()

    def is_closed(self) -> bool:
        """
        Check if the pool manager has been closed.

        Returns:
            bool: True if the pool manager is closed, False otherwise.
        """
        return self._closed
