from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def app():
    mock_app = MagicMock()
    mock_app.repo.path = "fake_repo"
    mock_app.abort = MagicMock()
    return mock_app


@pytest.fixture()
def mock_dashboard_env():
    with (
        patch("ddev.cli.size.create_dashboard.get_org") as mock_get_org,
        patch("ddev.cli.size.create_dashboard.requests.post") as mock_post,
    ):
        mock_get_org.return_value = {"api_key": "fake-api-key", "app_key": "fake-app-key", "site": "datadoghq.com"}
        mock_response = MagicMock()
        mock_response.json.return_value = {"url": "/dashboard/abc123"}
        mock_post.return_value = mock_response

        yield


def test_create_dashboard_success(ddev, app, mock_dashboard_env):
    result = ddev("size", "create-dashboard", "--dd-org", "default", obj=app)
    print(result.output)
    assert result.exit_code == 0
    assert "Dashboard URL: https://app.datadoghq.com/dashboard/abc123" in result.output


def test_create_dashboard_missing_api_key(ddev, app):
    with patch("ddev.cli.size.create_dashboard.get_org") as mock_get_org:
        mock_get_org.return_value = {"app_key": "fake-app-key", "site": "datadoghq.com"}

        result = ddev("size", "create-dashboard", "--dd-org", "default", obj=app)

        assert result.exit_code != 0
        assert "No API key found in config file" in result.output


def test_create_dashboard_missing_app_key(ddev, app):
    with patch("ddev.cli.size.create_dashboard.get_org") as mock_get_org:
        mock_get_org.return_value = {"api_key": "fake-api-key", "site": "datadoghq.com"}

        result = ddev("size", "create-dashboard", "--dd-org", "default", obj=app)

        assert result.exit_code != 0
        assert "No APP key found in config file" in result.output


def test_create_dashboard_missing_site(ddev, app):
    with patch("ddev.cli.size.create_dashboard.get_org") as mock_get_org:
        mock_get_org.return_value = {"api_key": "fake-api-key", "app_key": "fake-app-key"}

        result = ddev("size", "create-dashboard", "--dd-org", "default", obj=app)

        assert result.exit_code != 0
        assert "No site found in config file" in result.output
