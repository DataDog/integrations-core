# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import click
import httpx
from twine.commands.upload import upload
from twine.settings import Settings

from ddev.event_bus.exceptions import MessageProcessingError, ProcessorHookError
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator, SyncProcessor

if TYPE_CHECKING:
    from ddev.repo.core import Repository

# Names claimed on PyPI that must stay published as placeholders even though the command cannot
# select them from the repository: integrations that were later removed, and the build-time
# dependency provider, which the repository marks as not an integration.
KEPT_PLACEHOLDER_NAMES = (
    'datadog-datadog-csi-driver',
    'datadog-oracle',
    'datadog-snowflake',
    'datadog-tokumx',
    'datadog-datadog_checks_dependency_provider',
)

logger = logging.getLogger(__name__)


def _placeholder_package_names(repo: Repository) -> dict[str, str]:
    """Map each integration name to the PyPI package name it claims as a placeholder.

    Only integrations are claimed; the repository configuration marks non-integration packages
    (`ddev`, `datadog-checks-*`, the dependency provider) accordingly.
    """
    names: dict[str, str] = {}
    for integration in repo.integrations.iter_packages(['all']):
        if integration.is_integration:
            names[integration.name] = integration.project_metadata['project']['name']
    return names


def _resolve_placeholder_name(requested: str, package_names: dict[str, str]) -> str | None:
    """Resolve a user-requested name to its PyPI package name.

    Accepts an integration name (`n8n`), its dashed variant, or the package name itself
    (`datadog-n8n`), as well as the names of retired placeholders. Matching follows PyPI's
    name normalization: case is ignored, and dashes and underscores are equivalent.
    """
    normalized = requested.replace('_', '-').lower()
    for integration_name, package_name in package_names.items():
        if normalized in (integration_name.replace('_', '-'), package_name.replace('_', '-').lower()):
            return package_name
    for retired_name in KEPT_PLACEHOLDER_NAMES:
        if normalized == retired_name.replace('_', '-').lower():
            return retired_name
    return None


def _needs_placeholder(name: str, http_get: Callable[..., httpx.Response]) -> bool:
    """Return whether `name` is missing on PyPI or still at the empty 0.0.1 placeholder."""
    response = http_get(f'https://pypi.org/pypi/{name}/json', timeout=30)
    if response.status_code == 404:
        return True
    response.raise_for_status()
    return response.json()['info']['version'] == '0.0.1'


def _api_token(prompt: Callable[..., str], interactive: Callable[[], bool]) -> str | None:
    """Read a plain PyPI API token from the environment, or prompt for one in a terminal.

    The token is deliberately never a command-line flag so it cannot leak through shell history.
    """
    token = os.environ.get('DDEV_PYPI_TOKEN')
    if token:
        return token
    if interactive():
        return prompt('PyPI API token: ', hide_input=True)
    return None


def _mint_oidc_token(http_get: Callable[..., httpx.Response], http_post: Callable[..., httpx.Response]) -> str:
    """Exchange a fresh GitHub Actions OIDC token for a short-lived PyPI upload token.

    Trusted publishing: each exchange turns at most one pending publisher into a project and the
    minted token expires after 15 minutes, so every package mints its own token. The mint fails for
    projects that do not have this workflow registered as a trusted publisher.
    """
    request_url = os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']
    request_token = os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']
    response = http_get(
        request_url,
        # The runner's token URL already carries query parameters; httpx would replace them if
        # passed through `params`.
        params={**httpx.URL(request_url).params, 'audience': 'pypi'},
        headers={'Authorization': f'bearer {request_token}'},
        timeout=30,
    )
    response.raise_for_status()
    response = http_post(
        'https://pypi.org/_/oidc/github/mint-token', json={'token': response.json()['value']}, timeout=30
    )
    if response.status_code != 200:
        raise RuntimeError(f'PyPI refused to mint an upload token for this workflow: {response.text}')
    return response.json()['token']


def _build_placeholder(name: str, workdir: Path, run: Callable[..., Any]) -> Path:
    """Build the placeholder wheel for `name` in `workdir` and return its path."""
    module = name.replace('-', '_')
    project_dir = workdir / name
    docs_url = 'https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install'
    # PyPI deletes empty placeholder packages under its name-retention policy, so the placeholders
    # carry a README and an import-time pointer instead of being empty wheels.
    readme = (
        'Datadog reserves this name to protect users from typosquatting and dependency confusion. '
        'It is not a Datadog integration.\n'
        '\n'
        'Datadog integrations are installed and managed with the Datadog Agent, not with pip:\n'
        f'{docs_url}'
    )
    module_source = (
        f'print("This package only reserves its name on PyPI. It is not a Datadog integration. Datadog '
        f'integrations are installed with the Datadog Agent: {docs_url}")\n'
    )
    # The version must stay above 0.0.1: PyPI rejects re-uploading an already-published 0.0.1 wheel.
    pyproject = f'''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{name}"
version = "0.0.2"
readme = "README.md"

[tool.hatch.build.targets.wheel]
only-include = ["{module}"]
'''
    (project_dir / module).mkdir(parents=True)
    (project_dir / 'README.md').write_text(readme)
    (project_dir / module / '__init__.py').write_text(module_source)
    (project_dir / 'pyproject.toml').write_text(pyproject)
    try:
        run(
            [sys.executable, '-m', 'hatchling', 'build', '-t', 'wheel', '-d', 'dist'],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f'hatchling build failed for {name}: {e.stderr.decode(errors="replace")}') from e
    (wheel,) = (project_dir / 'dist').glob('*.whl')
    return wheel


def _upload_placeholder(wheel: Path, token: str) -> None:
    """Upload `wheel` to PyPI with `token`.

    Placeholders publish without provenance attestations: they are not consumed as dependencies,
    and `gh-action-pypi-publish` only attests uploads made through trusted publishing.
    """
    upload(
        Settings(
            repository_url='https://upload.pypi.org/legacy/',
            username='__token__',
            password=token,
            skip_existing=True,
            non_interactive=True,
        ),
        [str(wheel)],
    )


@dataclass
class PlaceholderReport:
    """What a `publish_placeholders` run selected, skipped, published, and failed at."""

    selected: list[str]
    skipped: list[str]
    published: set[str] = field(default_factory=set)
    failed: dict[str, Exception] = field(default_factory=dict)


@dataclass
class PlaceholderPorts:
    """The external dependencies of `publish_placeholders`, injectable for tests.

    The defaults run against real PyPI, GitHub Actions, hatchling, and twine.
    """

    http_get: Callable[..., httpx.Response] = field(default_factory=lambda: httpx.get)
    http_post: Callable[..., httpx.Response] = field(default_factory=lambda: httpx.post)
    run: Callable[..., Any] = field(default_factory=lambda: subprocess.run)
    upload: Callable[[Path, str], None] = _upload_placeholder
    prompt: Callable[..., str] = click.prompt
    interactive: Callable[[], bool] = lambda: sys.stdin.isatty() and sys.stdout.isatty()
    notify: Callable[[str, str], None] = lambda level, text: print(text)


@dataclass
class PlaceholderMessage(BaseMessage):
    """The `id` is the PyPI project name."""


class PlaceholderProcessor(SyncProcessor[PlaceholderMessage]):
    def __init__(self, report: PlaceholderReport, ports: PlaceholderPorts, token: str | None):
        super().__init__('placeholder-processor')
        self._report = report
        self._ports = ports
        # A plain token uploads every package; without one, each package mints its own
        # short-lived token through trusted publishing.
        self._token = token

    def process_message(self, message: PlaceholderMessage) -> None:
        with tempfile.TemporaryDirectory(prefix=message.id) as workdir:
            wheel = _build_placeholder(message.id, Path(workdir), self._ports.run)
            token = (
                self._token
                if self._token is not None
                else _mint_oidc_token(self._ports.http_get, self._ports.http_post)
            )
            self._ports.upload(wheel, token)

    async def on_success(self, message: PlaceholderMessage) -> None:
        self._report.published.add(message.id)
        self._ports.notify('success', f'  ok {message.id}')

    async def on_error(self, error: MessageProcessingError | ProcessorHookError) -> None:
        self._report.failed[error.message.id] = error.original_exception
        self._ports.notify('error', f'  FAIL {error.message.id}: {error.original_exception}')


class PlaceholderOrchestrator(EventBusOrchestrator):
    def __init__(self, report: PlaceholderReport, processor: PlaceholderProcessor, ports: PlaceholderPorts):
        super().__init__(
            logger=logger,
            max_timeout=3600.0,
            executor=ThreadPoolExecutor(max_workers=4),
        )
        self._report = report
        self._processor = processor
        self._ports = ports
        self.register_processor(processor, [PlaceholderMessage])

    async def on_initialize(self) -> None:
        for name in self._report.selected:
            self.submit_message(PlaceholderMessage(id=name))

    async def on_message_received(self, message: BaseMessage) -> None:
        """Required hook; per-package logging comes from the processor instead."""

    async def on_finalize(self, exception: Exception | None) -> None:
        if exception is not None:
            self._ports.notify('error', f'Error publishing placeholders: {exception}')
        self._ports.notify('info', f'Published {len(self._report.published)}, failed {len(self._report.failed)}')


def publish_placeholders(
    repo: Repository,
    names: tuple[str, ...] = (),
    dry_run: bool = False,
    ports: PlaceholderPorts | None = None,
) -> PlaceholderReport:
    """Publish placeholder packages to PyPI.

    With NAMES, publish only those integrations; each name may be an integration name (n8n) or a
    package name (datadog-n8n), and packages whose PyPI release is newer than the empty 0.0.1
    placeholder are skipped. Without NAMES, publish every package whose PyPI release is missing
    or still the empty 0.0.1 placeholder, including the names that no longer belong to an
    integration (retired names and the build-time dependency provider).

    Authentication: a plain token comes from the DDEV_PYPI_TOKEN environment variable or `prompt`;
    without one, each package mints its own short-lived token through GitHub trusted publishing,
    raising ValueError when neither is available.

    With dry_run, report what would be published without building or uploading anything.
    """
    ports = ports or PlaceholderPorts()
    package_names = _placeholder_package_names(repo)
    if names:
        resolved_names = []
        for requested in names:
            resolved = _resolve_placeholder_name(requested, package_names)
            if resolved is None:
                raise ValueError(f'Unknown integration or package name: {requested}')
            resolved_names.append(resolved)
        resolved_names = sorted(set(resolved_names))
    else:
        resolved_names = sorted(set(package_names.values()) | set(KEPT_PLACEHOLDER_NAMES))

    report = PlaceholderReport(selected=[], skipped=[])
    ports.notify('info', f'Checking {len(resolved_names)} names on PyPI...')
    for name in resolved_names:
        try:
            if _needs_placeholder(name, ports.http_get):
                report.selected.append(name)
            else:
                report.skipped.append(name)
        except httpx.HTTPError as error:
            report.failed[name] = error
            ports.notify('error', f'  FAIL {name}: PyPI check failed: {error}')
    if names:
        for name in report.skipped:
            ports.notify('info', f'  skip {name} (already published)')

    if not report.selected or dry_run:
        return report

    token = _api_token(ports.prompt, ports.interactive)
    oidc_publishing = 'ACTIONS_ID_TOKEN_REQUEST_URL' in os.environ and 'ACTIONS_ID_TOKEN_REQUEST_TOKEN' in os.environ
    if token is None and not oidc_publishing:
        raise ValueError(
            'No PyPI API token available: set DDEV_PYPI_TOKEN, enter one at the prompt, '
            'or run in GitHub Actions with trusted publishing.'
        )

    orchestrator = PlaceholderOrchestrator(report, PlaceholderProcessor(report, ports, token), ports)
    orchestrator.run()
    if orchestrator.shutdown_request is not None:
        # A stopped run misses the success and error hooks of whatever was still in flight, so
        # its report cannot be trusted as an outcome.
        raise ValueError(f'Publishing placeholders stopped: {orchestrator.shutdown_request.kind.name.lower()}')
    return report
