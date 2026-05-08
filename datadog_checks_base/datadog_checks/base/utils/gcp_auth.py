# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import base64
import datetime
import json
import os
from dataclasses import dataclass, field

import requests

_GCLOUD_ADC_PATH = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")

_METADATA_TOKEN_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
)


@dataclass
class GcpCredentials:
    token: str
    expiry: datetime.datetime | None
    service_account_email: str = field(default="user")


def load_credentials_from_file(path: str, scopes: list[str]) -> GcpCredentials:
    """Load a service_account or authorized_user JSON key file and return a fresh token."""
    with open(path) as f:
        key = json.load(f)

    cred_type = key.get("type")
    if cred_type == "service_account":
        return _fetch_service_account_token(key, scopes)
    elif cred_type == "authorized_user":
        return _fetch_authorized_user_token(key)
    else:
        raise ValueError(f"Unsupported GCP credential type: {cred_type!r}")


def default(scopes: list[str]) -> GcpCredentials:
    """Application Default Credentials chain — mirrors google.auth.default()."""
    adc_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if adc_path:
        return load_credentials_from_file(adc_path, scopes)

    if os.path.exists(_GCLOUD_ADC_PATH):
        return load_credentials_from_file(_GCLOUD_ADC_PATH, scopes)

    try:
        return _fetch_metadata_token()
    except Exception as e:
        raise Exception(
            "Could not find GCP credentials. Checked GOOGLE_APPLICATION_CREDENTIALS env var, "
            f"{_GCLOUD_ADC_PATH}, and GCE/GKE metadata server. Metadata server error: {e}"
        ) from e


def _fetch_service_account_token(key: dict, scopes: list[str]) -> GcpCredentials:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    token_uri = key.get("token_uri", "https://oauth2.googleapis.com/token")
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

    header = _b64json({"alg": "RS256", "typ": "JWT"})
    claims = _b64json(
        {
            "iss": key["client_email"],
            "sub": key["client_email"],
            "scope": " ".join(scopes),
            "aud": token_uri,
            "iat": now,
            "exp": now + 3600,
        }
    )
    message = f"{header}.{claims}".encode("utf-8")

    private_key = serialization.load_pem_private_key(key["private_key"].encode("utf-8"), password=None)
    signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")

    resp = requests.post(
        token_uri,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": f"{header}.{claims}.{sig_b64}",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=data.get("expires_in", 3600))
    return GcpCredentials(token=data["access_token"], expiry=expiry, service_account_email=key["client_email"])


def _fetch_authorized_user_token(creds: dict) -> GcpCredentials:
    token_uri = creds.get("token_uri", "https://oauth2.googleapis.com/token")
    resp = requests.post(
        token_uri,
        data={
            "grant_type": "refresh_token",
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": creds["refresh_token"],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=data.get("expires_in", 3600))
    return GcpCredentials(token=data["access_token"], expiry=expiry)


def _fetch_metadata_token() -> GcpCredentials:
    resp = requests.get(
        _METADATA_TOKEN_URL,
        headers={"Metadata-Flavor": "Google"},
        timeout=3,
    )
    resp.raise_for_status()
    data = resp.json()

    expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=data.get("expires_in", 3600))
    return GcpCredentials(token=data["access_token"], expiry=expiry)


def _b64json(obj: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode("utf-8")).decode("utf-8").rstrip("=")
