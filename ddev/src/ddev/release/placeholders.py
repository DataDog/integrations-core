# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import getpass
import os
import subprocess
import sys
import tempfile
import tomllib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from ddev.event_bus.exceptions import MessageProcessingError, ProcessorHookError
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator, SyncProcessor

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.repo.core import Repository

PLACEHOLDER_VERSION = '0.0.2'
INSTALL_DOCS_URL = 'https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install'
PYPI_JSON_URL = 'https://pypi.org/pypi/{name}/json'
PYPI_MINT_TOKEN_URL = 'https://pypi.org/_/oidc/github/mint-token'
PYPI_UPLOAD_URL = 'https://upload.pypi.org/legacy/'
TOKEN_ENV_VAR = 'DDEV_PYPI_TOKEN'

# PyPI deletes empty placeholder packages under its name-retention policy, so the placeholders carry a
# README and an import-time pointer instead of being empty wheels. The version must stay above 0.0.1:
# PyPI rejects re-uploading an already-published 0.0.1 wheel.
README_TEMPLATE = (
    'Datadog reserves this name to protect users from typosquatting and dependency confusion. '
    'It is not a Datadog integration.\n'
    '\n'
    'Datadog integrations are installed and managed with the Datadog Agent, not with pip:\n'
    f'{INSTALL_DOCS_URL}'
)

MODULE_TEMPLATE = (
    f'print("This package only reserves its name on PyPI. It is not a Datadog integration. Datadog '
    f'integrations are installed with the Datadog Agent: {INSTALL_DOCS_URL}")\n'
)

PYPROJECT_TEMPLATE = '''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{name}"
version = "{version}"
readme = "README.md"

[tool.hatch.build.targets.wheel]
only-include = ["{module}"]
'''

# Names claimed on PyPI for integrations that were later removed from this repository. They are kept
# published as placeholders so the names cannot be re-registered by anyone else.
RETIRED_PLACEHOLDER_NAMES = (
    'datadog-datadog-csi-driver',
    'datadog-oracle',
    'datadog-snowflake',
    'datadog-tokumx',
)

# Real packages maintained in this repository. They are published through their own release process
# and must never be overwritten with a placeholder.
EXCLUDED_PACKAGE_NAMES = frozenset(
    {
        'ddev',
        'datadog-checks-base',
        'datadog-checks-dev',
        'datadog-checks-downloader',
    }
)


def placeholder_package_names(repo: Repository) -> dict[str, str]:
    """Map each integration name to the PyPI package name it claims as a placeholder.

    Real packages shipped from this repository are excluded: only `datadog-*` integration names
    are claimed.
    """
    names: dict[str, str] = {}
    for integration in repo.integrations.iter_packages(['all']):
        path = integration.path / 'pyproject.toml'
        if not path.is_file():
            continue
        package_name = tomllib.loads(path.read_text())['project']['name']
        if package_name not in EXCLUDED_PACKAGE_NAMES:
            names[integration.name] = package_name
    return names


def resolve_placeholder_name(requested: str, package_names: dict[str, str]) -> str | None:
    """Resolve a user-requested name to its PyPI package name.

    Accepts an integration name (`n8n`), its dashed variant, or the package name itself
    (`datadog-n8n`), as well as the names of retired placeholders.
    """
    normalized = requested.replace('-', '_')
    for integration_name, package_name in package_names.items():
        if requested in (integration_name, package_name) or normalized == integration_name:
            return package_name
    if requested in RETIRED_PLACEHOLDER_NAMES:
        return requested
    return None


def needs_placeholder(name: str) -> bool:
    """Return whether `name` is missing on PyPI or still at the empty 0.0.1 placeholder."""
    response = httpx.get(PYPI_JSON_URL.format(name=name), timeout=30)
    if response.status_code == 404:
        return True
    response.raise_for_status()
    return response.json()['info']['version'] == '0.0.1'


def get_api_token() -> str | None:
    """Read a plain PyPI API token from the environment, or prompt for one in a terminal.

    The token is deliberately never a command-line flag so it cannot leak through shell history.
    """
    token = os.environ.get(TOKEN_ENV_VAR)
    if token:
        return token
    if sys.stdin.isatty() and sys.stdout.isatty():
        return getpass.getpass('PyPI API token: ')
    return None


def oidc_publishing_available() -> bool:
    """Return whether this process runs in GitHub Actions with an OIDC token to exchange."""
    return 'ACTIONS_ID_TOKEN_REQUEST_URL' in os.environ and 'ACTIONS_ID_TOKEN_REQUEST_TOKEN' in os.environ


def mint_oidc_token() -> str:
    """Exchange a fresh GitHub Actions OIDC token for a short-lived PyPI upload token.

    Trusted publishing: each exchange turns at most one pending publisher into a project and the
    minted token expires after 15 minutes, so every package mints its own token. The mint fails for
    projects that do not have this workflow registered as a trusted publisher.
    """
    request_url = os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']
    request_token = os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']
    response = httpx.get(
        request_url,
        params={'audience': 'pypi'},
        headers={'Authorization': f'bearer {request_token}'},
        timeout=30,
    )
    response.raise_for_status()
    response = httpx.post(PYPI_MINT_TOKEN_URL, json={'token': response.json()['value']}, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f'PyPI refused to mint an upload token for this workflow: {response.text}')
    return response.json()['token']


def build_placeholder(name: str, workdir: Path) -> Path:
    """Build the placeholder wheel for `name` in `workdir` and return its path."""
    module = name.replace('-', '_')
    project_dir = workdir / name
    (project_dir / module).mkdir(parents=True)
    (project_dir / 'README.md').write_text(README_TEMPLATE)
    (project_dir / module / '__init__.py').write_text(MODULE_TEMPLATE)
    (project_dir / 'pyproject.toml').write_text(
        PYPROJECT_TEMPLATE.format(name=name, module=module, version=PLACEHOLDER_VERSION)
    )
    subprocess.run(
        [sys.executable, '-m', 'hatchling', 'build', '-t', 'wheel', '-d', 'dist'],
        cwd=project_dir,
        check=True,
        capture_output=True,
    )
    (wheel,) = (project_dir / 'dist').glob('*.whl')
    return wheel


def upload_placeholder(wheel: Path, token: str) -> None:
    """Upload `wheel` to PyPI with `token`.

    Placeholders publish without provenance attestations: they are not consumed as dependencies,
    and `gh-action-pypi-publish` only attests uploads made through trusted publishing.
    """
    from twine.commands.upload import upload
    from twine.settings import Settings

    upload(
        Settings(
            repository_url=PYPI_UPLOAD_URL,
            username='__token__',
            password=token,
            skip_existing=True,
            non_interactive=True,
        ),
        [str(wheel)],
    )


@dataclass
class PlaceholderMessage(BaseMessage):
    """The `id` is the PyPI project name."""


class PlaceholderProcessor(SyncProcessor[PlaceholderMessage]):
    def __init__(self, app: Application, token: str | None):
        super().__init__('placeholder-processor')
        self._app = app
        # A plain token uploads every package; without one, each package mints its own
        # short-lived token through trusted publishing.
        self._token = token
        self.published: set[str] = set()
        self.failed: dict[str, Exception] = {}

    def process_message(self, message: PlaceholderMessage) -> None:
        with tempfile.TemporaryDirectory(prefix=message.id) as workdir:
            wheel = build_placeholder(message.id, Path(workdir))
            upload_placeholder(wheel, self._token or mint_oidc_token())

    async def on_success(self, message: PlaceholderMessage) -> None:
        self.published.add(message.id)
        self._app.display_success(f'  ok {message.id}')

    async def on_error(self, error: MessageProcessingError | ProcessorHookError) -> None:
        self.failed[error.message.id] = error.original_exception
        self._app.display_error(f'  FAIL {error.message.id}: {error.original_exception}')


class PlaceholderOrchestrator(EventBusOrchestrator):
    def __init__(
        self,
        app: Application,
        names: list[str],
        token: str | None,
        max_workers: int = 4,
        max_timeout: float = 3600.0,
    ):
        super().__init__(
            logger=app.logger,
            max_timeout=max_timeout,
            executor=ThreadPoolExecutor(max_workers=max_workers),
        )
        self._app = app
        self._names = names
        self._processor = PlaceholderProcessor(app, token)
        self.register_processor(self._processor, [PlaceholderMessage])

    async def on_initialize(self) -> None:
        for name in self._names:
            self.submit_message(PlaceholderMessage(id=name))

    async def on_message_received(self, message: BaseMessage) -> None:
        self._app.display_info(f'Publishing {message.id}')

    async def on_finalize(self, exception: Exception | None) -> None:
        if exception is not None:
            self._app.display_error(f'Error publishing placeholders: {exception}')
        self._app.display_info(f'Published {len(self._processor.published)}, failed {len(self._processor.failed)}')

    @property
    def had_failures(self) -> bool:
        return bool(self._processor.failed)
