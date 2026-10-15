# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import io
import tarfile
from collections.abc import Iterator
from typing import TYPE_CHECKING

import httpx
import pytest

from ddev.cli.validate import licenses_utils
from ddev.cli.validate.licenses import scrape_copyright_data
from ddev.utils.fs import Path
from ddev.utils.network import REQUEST_ATTEMPTS
from ddev.utils.toml import dump_toml_data, load_toml_file

if TYPE_CHECKING:
    from unittest.mock import MagicMock

# The mock transport rejects any request without an installed handler, so the early-error
# and extras-skip cases are covered against accidental network access too.
pytestmark = pytest.mark.usefixtures('mock_http')

PACKAGE_NAME = 'fake-package'
PACKAGE_VERSION = '1.2.3'
TARBALL_URL = f'https://files.pythonhosted.org/packages/{PACKAGE_NAME}-{PACKAGE_VERSION}.tar.gz'
PYPI_URL = f'https://pypi.org/pypi/{PACKAGE_NAME}/{PACKAGE_VERSION}/json'
SPDX_URL = 'https://raw.githubusercontent.com/spdx/license-list-data/v3.13/json/licenses.json'
COPYRIGHT = 'Copyright (c) 2020 Fake Author'
EXPECTED_CSV = """Component,Origin,License,Copyright
fake-package,PyPI,MIT,Copyright (c) 2020 Fake Author
"""


def build_tar_gz(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def archive_bytes() -> bytes:
    return build_tar_gz({f'{PACKAGE_NAME}-{PACKAGE_VERSION}/LICENSE': f'# {COPYRIGHT}\n'.encode()})


def tarball_response() -> httpx.Response:
    return httpx.Response(200, content=archive_bytes())


class InterruptedStream(httpx.SyncByteStream):
    """Yields part of a response body, then raises like an interrupted download."""

    def __init__(self, error: httpx.ReadError | httpx.ReadTimeout | httpx.RemoteProtocolError) -> None:
        self.error = error

    def __iter__(self) -> Iterator[bytes]:
        yield archive_bytes()[:64]
        raise self.error


def interrupted_response(error: httpx.ReadError | httpx.ReadTimeout | httpx.RemoteProtocolError) -> httpx.Response:
    return httpx.Response(200, stream=InterruptedStream(error))


def pypi_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            'info': {
                'name': PACKAGE_NAME,
                'version': PACKAGE_VERSION,
                'author': '',
                'maintainer': '',
                'author_email': '',
                'maintainer_email': '',
                'home_page': '',
                'license': '',
                'license_expression': 'MIT',
                'classifiers': [],
            },
            'urls': [{'url': TARBALL_URL}],
        },
    )


def spdx_response() -> httpx.Response:
    return httpx.Response(200, json={'licenses': [{'licenseId': 'Apache-2.0'}, {'licenseId': 'MIT'}]})


def install_license_handlers(mock_http: MagicMock) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == PYPI_URL:
            return pypi_response()
        elif url == SPDX_URL:
            return spdx_response()
        elif url == TARBALL_URL:
            return tarball_response()
        raise AssertionError(f'Unexpected HTTP request in test: {url}')

    mock_http.side_effect = respond


def write_requirements(repo_path: Path, *lines: str) -> None:
    path = repo_path / 'agent_requirements.in'
    path.write_text(''.join(lines) or f'{PACKAGE_NAME}=={PACKAGE_VERSION}\n', encoding='utf-8')


@pytest.mark.parametrize(
    'name, contents, expected_error_output',
    [
        pytest.param(
            'licenses',
            {'dummy_package': 'dummy_license'},
            'EXPLICIT_LICENSES contains additional package not in agent',
            id='explicit licenses',
        ),
        pytest.param(
            'repo',
            {'dummy_package': 'https://github.com/dummy_package'},
            'PACKAGE_REPO_OVERRIDES contains additional package not in agent',
            id='package repo overrides',
        ),
    ],
)
def test_error_extra_dependency(name, contents, expected_error_output, ddev, fake_repo, helpers):
    write_requirements(fake_repo.path)

    ddev_config_path = fake_repo.path / '.ddev' / 'config.toml'

    data = load_toml_file(ddev_config_path)

    data['overrides']['dependencies'] = {name: contents}

    dump_toml_data(data, ddev_config_path)

    result = ddev('validate', 'licenses')

    assert result.exit_code == 1, result.output

    # Check if expected error validation error message is in output
    assert expected_error_output in helpers.remove_trailing_spaces(result.output)


@pytest.mark.parametrize(
    'repo_fixture, expected_exit_code, expected_message',
    [
        pytest.param('fake_repo', 0, 'Passed: 1', id='Core integrations'),
        pytest.param(
            'fake_extras_repo',
            1,
            'License validation is only available for repo `core`, skipping for repo `extras`',
            id='Extras integrations',
        ),
    ],
)
def test_validate_repo(
    repo_fixture, expected_exit_code, expected_message, ddev, helpers, config_file, monkeypatch, mock_http, request
):
    repo = request.getfixturevalue(repo_fixture)

    if repo.name == 'core':
        write_requirements(repo.path)
        (repo.path / 'LICENSE-3rdparty.csv').write_text(EXPECTED_CSV, encoding='utf-8')
        # Replace the production extras with a controlled empty set so the expected CSV
        # only depends on this test's fixture data.
        monkeypatch.setattr(licenses_utils, 'ADDITIONAL_LICENSES', set())
        install_license_handlers(mock_http)

    result = ddev('validate', 'licenses')

    assert result.exit_code == expected_exit_code, result.output
    assert expected_message in helpers.remove_trailing_spaces(result.output)


def test_error_no_requirements_file(fake_repo, ddev, helpers):
    result = ddev('validate', 'licenses')

    assert result.exit_code == 1

    expected_error_output = 'Requirements file is not found. Out of sync, run'
    assert expected_error_output in helpers.remove_trailing_spaces(result.output)


def test_invalid_requirement(fake_repo, ddev, helpers):
    write_requirements(fake_repo.path, "aerospike==^4.0.0; sys_platform != 'win32' and sys_platform != 'darwin'\n")

    result = ddev('validate', 'licenses')

    assert result.exit_code == 1

    expected_error_output = 'InvalidRequirement error'
    assert expected_error_output in helpers.remove_trailing_spaces(result.output)
    assert 'aerospike==^4.0.0' in helpers.remove_trailing_spaces(result.output)


@pytest.mark.parametrize(
    'error',
    [
        pytest.param(httpx.ConnectError('[WinError 10054] connection reset'), id='connect error'),
        pytest.param(httpx.ConnectTimeout('connection timed out'), id='connect timeout'),
    ],
)
def test_scrape_recovers_from_transient_connection_failure(
    monkeypatch: pytest.MonkeyPatch, mock_http: MagicMock, error: httpx.ConnectError | httpx.ConnectTimeout
):
    attempts: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        assert (request.method, str(request.url)) == ('GET', TARBALL_URL)
        attempts.append(request)
        if len(attempts) == 1:
            raise error
        return tarball_response()

    mock_http.side_effect = respond

    assert scrape_copyright_data(TARBALL_URL) == COPYRIGHT
    assert len(attempts) == 2


def test_scrape_persistent_connection_failure_raises(monkeypatch: pytest.MonkeyPatch, mock_http: MagicMock):
    attempts: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        assert (request.method, str(request.url)) == ('GET', TARBALL_URL)
        attempts.append(request)
        assert len(attempts) <= REQUEST_ATTEMPTS, f'unbounded retries: {len(attempts)} attempts'
        raise httpx.ConnectError('[WinError 10054] connection reset')

    mock_http.side_effect = respond

    with pytest.raises(httpx.ConnectError):
        scrape_copyright_data(TARBALL_URL)

    assert len(attempts) == REQUEST_ATTEMPTS


@pytest.mark.parametrize(
    'error',
    [
        pytest.param(httpx.ReadError('read error'), id='read error'),
        pytest.param(httpx.ReadTimeout('read timed out'), id='read timeout'),
        pytest.param(
            httpx.RemoteProtocolError('peer closed connection without sending complete message body'),
            id='remote protocol error',
        ),
    ],
)
def test_scrape_recovers_from_interruption_during_response(
    monkeypatch: pytest.MonkeyPatch,
    mock_http: MagicMock,
    error: httpx.ReadError | httpx.ReadTimeout | httpx.RemoteProtocolError,
):
    attempts: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        assert (request.method, str(request.url)) == ('GET', TARBALL_URL)
        attempts.append(request)
        if len(attempts) == 1:
            return interrupted_response(error)
        return tarball_response()

    mock_http.side_effect = respond

    assert scrape_copyright_data(TARBALL_URL) == COPYRIGHT
    assert len(attempts) == 2


def test_scrape_persistent_interruption_during_response_raises(monkeypatch: pytest.MonkeyPatch, mock_http: MagicMock):
    attempts: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        assert (request.method, str(request.url)) == ('GET', TARBALL_URL)
        attempts.append(request)
        assert len(attempts) <= REQUEST_ATTEMPTS, f'unbounded retries: {len(attempts)} attempts'
        return interrupted_response(httpx.ReadError('read error'))

    mock_http.side_effect = respond

    with pytest.raises(httpx.ReadError):
        scrape_copyright_data(TARBALL_URL)

    assert len(attempts) == REQUEST_ATTEMPTS


def test_scrape_http_status_error_is_actionable(mock_http: MagicMock):
    attempts: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        assert (request.method, str(request.url)) == ('GET', TARBALL_URL)
        attempts.append(request)
        return httpx.Response(404, text='Not Found')

    mock_http.side_effect = respond

    with pytest.raises(httpx.HTTPStatusError):
        scrape_copyright_data(TARBALL_URL)

    assert len(attempts) == 1
