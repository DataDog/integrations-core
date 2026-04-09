# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading
import time

try:
    import google.auth
    import google.auth.exceptions
    import google.auth.impersonated_credentials
    import google.auth.transport.requests

    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False

from datadog_checks.base import ConfigurationError

GCP_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
TOKEN_TTL_SECONDS = 55 * 60  # 55 minutes; GCP tokens expire at 60


class GCPIAMTokenProvider:
    """Generates and caches GCP IAM access tokens for Memorystore Redis/Valkey IAM auth.

    The Redis AUTH username for Memorystore is always "default" per Google's docs;
    the service account is only used for ADC impersonation, not as the Redis username.
    """

    def __init__(self, service_account: str | None = None):
        if not HAS_GOOGLE_AUTH:
            raise ConfigurationError(
                "The 'google-auth' package is required for GCP IAM authentication. "
                "Install it with: pip install datadog-checks-redisdb[gcp]"
            )
        try:
            source_credentials, _ = google.auth.default(scopes=[GCP_SCOPE])
        except google.auth.exceptions.DefaultCredentialsError as e:
            raise ConfigurationError(
                "GCP IAM auth: could not find application default credentials. "
                "Set GOOGLE_APPLICATION_CREDENTIALS or use GKE Workload Identity. "
                f"Original error: {e}"
            ) from e

        if service_account:
            self._credentials = google.auth.impersonated_credentials.Credentials(
                source_credentials=source_credentials,
                target_principal=service_account,
                target_scopes=[GCP_SCOPE],
            )
        else:
            self._credentials = source_credentials

        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_at: float = 0.0

    @property
    def username(self) -> str:
        return "default"

    def get_token(self) -> str:
        now = time.time()
        with self._lock:
            if self._token is None or now >= self._expires_at:
                self._token, self._expires_at = self._fetch_token()
            return self._token

    def _fetch_token(self) -> tuple[str, float]:
        request = google.auth.transport.requests.Request()
        self._credentials.refresh(request)
        return self._credentials.token, time.time() + TOKEN_TTL_SECONDS

    def is_token_expired(self) -> bool:
        return time.time() >= self._expires_at

    def invalidate(self) -> None:
        with self._lock:
            self._expires_at = 0.0
