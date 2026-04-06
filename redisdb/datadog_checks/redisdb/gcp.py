# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
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
TOKEN_TTL = 55 * 60  # 55 minutes; GCP tokens expire at 60


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

        self._token_fetched_at: float = 0.0

    @property
    def username(self) -> str:
        return "default"

    def get_token(self) -> str:
        if self.is_token_expired():
            request = google.auth.transport.requests.Request()
            self._credentials.refresh(request)
            self._token_fetched_at = time.monotonic()
        return self._credentials.token

    def is_token_expired(self) -> bool:
        return time.monotonic() - self._token_fetched_at >= TOKEN_TTL

    def invalidate(self) -> None:
        self._token_fetched_at = 0.0
