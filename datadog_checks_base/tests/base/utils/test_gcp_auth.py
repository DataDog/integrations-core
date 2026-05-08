# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from unittest import mock

import pytest

from datadog_checks.base.utils.gcp_auth import GcpCredentials, default, load_credentials_from_file


def _make_service_account_key() -> dict:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "key-id-123",
        "private_key": pem.decode("utf-8"),
        "client_email": "test-sa@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "token_uri": "https://oauth2.googleapis.com/token",
    }


def _make_authorized_user_key() -> dict:
    return {
        "type": "authorized_user",
        "client_id": "client-id.apps.googleusercontent.com",
        "client_secret": "client-secret",
        "refresh_token": "refresh-token-value",
        "token_uri": "https://oauth2.googleapis.com/token",
    }


def _mock_token_response(token: str, expires_in: int = 3600) -> mock.Mock:
    resp = mock.Mock()
    resp.json.return_value = {"access_token": token, "expires_in": expires_in, "token_type": "Bearer"}
    resp.raise_for_status = mock.Mock()
    return resp


class TestGcpCredentials:
    def test_defaults(self):
        creds = GcpCredentials(token="tok", expiry=None)
        assert creds.token == "tok"
        assert creds.expiry is None
        assert creds.service_account_email == "user"

    def test_with_service_account_email(self):
        creds = GcpCredentials(
            token="tok", expiry=None, service_account_email="sa@proj.iam.gserviceaccount.com"
        )
        assert creds.service_account_email == "sa@proj.iam.gserviceaccount.com"


class TestLoadCredentialsFromFile:
    def test_service_account_returns_token(self):
        key = _make_service_account_key()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(key, f)
            path = f.name

        try:
            with mock.patch(
                "datadog_checks.base.utils.gcp_auth.requests.post",
                return_value=_mock_token_response("ya29.service-token"),
            ):
                creds = load_credentials_from_file(path, scopes=["https://www.googleapis.com/auth/cloud-platform"])
        finally:
            os.unlink(path)

        assert creds.token == "ya29.service-token"
        assert creds.service_account_email == key["client_email"]
        assert creds.expiry is not None

    def test_service_account_posts_jwt_to_token_uri(self):
        key = _make_service_account_key()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(key, f)
            path = f.name

        try:
            with mock.patch(
                "datadog_checks.base.utils.gcp_auth.requests.post",
                return_value=_mock_token_response("tok"),
            ) as mock_post:
                load_credentials_from_file(path, scopes=["https://www.googleapis.com/auth/cloud-platform"])
        finally:
            os.unlink(path)

        mock_post.assert_called_once()
        url, = mock_post.call_args[0]
        assert url == "https://oauth2.googleapis.com/token"
        data = mock_post.call_args[1]["data"]
        assert data["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"
        assert "assertion" in data

    def test_authorized_user_returns_token(self):
        creds_data = _make_authorized_user_key()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(creds_data, f)
            path = f.name

        try:
            with mock.patch(
                "datadog_checks.base.utils.gcp_auth.requests.post",
                return_value=_mock_token_response("ya29.user-token"),
            ) as mock_post:
                creds = load_credentials_from_file(path, scopes=[])
        finally:
            os.unlink(path)

        assert creds.token == "ya29.user-token"
        assert creds.service_account_email == "user"
        data = mock_post.call_args[1]["data"]
        assert data["grant_type"] == "refresh_token"
        assert data["refresh_token"] == "refresh-token-value"

    def test_unknown_credential_type_raises(self):
        creds_data = {"type": "external_account", "audience": "//iam.googleapis.com/projects/123"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(creds_data, f)
            path = f.name

        try:
            with pytest.raises(ValueError, match="external_account"):
                load_credentials_from_file(path, scopes=[])
        finally:
            os.unlink(path)


class TestDefault:
    def test_uses_google_application_credentials_env_var(self):
        key = _make_service_account_key()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(key, f)
            path = f.name

        try:
            with mock.patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": path}):
                with mock.patch(
                    "datadog_checks.base.utils.gcp_auth.requests.post",
                    return_value=_mock_token_response("env-var-token"),
                ):
                    creds = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        finally:
            os.unlink(path)

        assert creds.token == "env-var-token"

    def test_falls_back_to_gcloud_credentials_file(self):
        creds_data = _make_authorized_user_key()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(creds_data, f)
            fake_gcloud_path = f.name

        env_without_adc = {k: v for k, v in os.environ.items() if k != "GOOGLE_APPLICATION_CREDENTIALS"}
        try:
            with mock.patch.dict(os.environ, env_without_adc, clear=True):
                with mock.patch("datadog_checks.base.utils.gcp_auth._GCLOUD_ADC_PATH", fake_gcloud_path):
                    with mock.patch(
                        "datadog_checks.base.utils.gcp_auth.requests.post",
                        return_value=_mock_token_response("gcloud-token"),
                    ):
                        creds = default(scopes=[])
        finally:
            os.unlink(fake_gcloud_path)

        assert creds.token == "gcloud-token"

    def test_falls_back_to_metadata_server(self):
        env_without_adc = {k: v for k, v in os.environ.items() if k != "GOOGLE_APPLICATION_CREDENTIALS"}
        with mock.patch.dict(os.environ, env_without_adc, clear=True):
            with mock.patch("datadog_checks.base.utils.gcp_auth._GCLOUD_ADC_PATH", "/nonexistent/path"):
                with mock.patch(
                    "datadog_checks.base.utils.gcp_auth.requests.get",
                    return_value=_mock_token_response("metadata-token"),
                ):
                    creds = default(scopes=[])

        assert creds.token == "metadata-token"

    def test_raises_when_all_sources_fail(self):
        env_without_adc = {k: v for k, v in os.environ.items() if k != "GOOGLE_APPLICATION_CREDENTIALS"}
        with mock.patch.dict(os.environ, env_without_adc, clear=True):
            with mock.patch("datadog_checks.base.utils.gcp_auth._GCLOUD_ADC_PATH", "/nonexistent/path"):
                with mock.patch(
                    "datadog_checks.base.utils.gcp_auth.requests.get",
                    side_effect=Exception("Connection refused"),
                ):
                    with pytest.raises(Exception, match="Could not find GCP credentials"):
                        default(scopes=[])

    def test_env_var_takes_priority_over_gcloud(self):
        key = _make_service_account_key()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(key, f)
            env_var_path = f.name

        gcloud_data = _make_authorized_user_key()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(gcloud_data, f)
            fake_gcloud_path = f.name

        try:
            with mock.patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": env_var_path}):
                with mock.patch("datadog_checks.base.utils.gcp_auth._GCLOUD_ADC_PATH", fake_gcloud_path):
                    with mock.patch(
                        "datadog_checks.base.utils.gcp_auth.requests.post",
                        return_value=_mock_token_response("env-var-wins"),
                    ) as mock_post:
                        creds = default(scopes=[])
        finally:
            os.unlink(env_var_path)
            os.unlink(fake_gcloud_path)

        assert creds.token == "env-var-wins"
        assert creds.service_account_email == key["client_email"]

    def test_expiry_is_in_future(self):
        env_without_adc = {k: v for k, v in os.environ.items() if k != "GOOGLE_APPLICATION_CREDENTIALS"}
        with mock.patch.dict(os.environ, env_without_adc, clear=True):
            with mock.patch("datadog_checks.base.utils.gcp_auth._GCLOUD_ADC_PATH", "/nonexistent/path"):
                with mock.patch(
                    "datadog_checks.base.utils.gcp_auth.requests.get",
                    return_value=_mock_token_response("tok", expires_in=3600),
                ):
                    creds = default(scopes=[])

        now = datetime.now(timezone.utc)
        assert creds.expiry is not None
        assert creds.expiry > now
