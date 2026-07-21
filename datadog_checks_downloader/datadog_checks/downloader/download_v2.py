# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""TUF pointer-file downloader for the v2 repository format."""

from __future__ import annotations

import hashlib
import importlib.resources
import json
import logging
import posixpath
import re
import tempfile
import urllib.request
from collections.abc import Mapping
from pathlib import Path

from tuf.ngclient import Updater
from tuf.ngclient.config import UpdaterConfig

from .exceptions import (
    DigestMismatch,
    LengthMismatch,
    MalformedPointerError,
    MissingVersion,
    TargetNotFoundError,
)

logger = logging.getLogger(__name__)

V2_REPOSITORY_URL = "https://agent-integration-wheels.datadoghq.com"

# tuf.ngclient sets its own fetcher timeout; this applies only to the raw wheel urlopen().
WHEEL_FETCH_TIMEOUT_SECONDS = 60

REQUIRED_POINTER_KEYS = ('digest', 'length', 'wheel_path')
V2_POINTER_TARGET_DELEGATION = 'wheelsmith'
V2_POINTER_TARGET_SCHEMA_VERSION = 'v1'
V2_POINTER_TARGET_PREFIX = f'{V2_POINTER_TARGET_DELEGATION}/{V2_POINTER_TARGET_SCHEMA_VERSION}'
SHA256_HEX_RE = re.compile(r'^[0-9a-f]{64}$')


class TUFPointerDownloader:
    """Downloads Datadog integration wheels from a v2 TUF repository."""

    def __init__(self, repository_url: str, disable_verification: bool = False):
        self._repository_url = repository_url.rstrip('/')
        self._disable_verification = disable_verification

        if disable_verification:
            logger.warning('Running with TUF verification disabled. Integrity is protected only by TLS (HTTPS).')

    def _bootstrap_metadata_dir(self, metadata_dir: Path) -> None:
        dest = metadata_dir / 'root.json'
        metadata = importlib.resources.files('datadog_checks.downloader') / 'data' / 'v2' / 'metadata'
        dest.write_bytes((metadata / 'root.json').read_bytes())

    def _make_updater(self, metadata_dir: Path, target_dir: Path) -> Updater:
        return Updater(
            metadata_dir=str(metadata_dir),
            metadata_base_url=f'{self._repository_url}/metadata/',
            target_base_url=f'{self._repository_url}/targets/',
            target_dir=str(target_dir),
            config=UpdaterConfig(prefix_targets_with_hash=True),
        )

    @staticmethod
    def _target_path(project: str, version: str | None) -> str:
        name = version if version is not None else 'latest'
        return f'{V2_POINTER_TARGET_PREFIX}/{project}/{name}.json'

    @staticmethod
    def _wheel_filename(project: str, version: str) -> str:
        distribution = project.replace('-', '_')
        return f'{distribution}-{version}-py3-none-any.whl'

    def _direct_wheel_url(self, project: str, version: str) -> str:
        return f'{self._repository_url}/wheels/{project}/{self._wheel_filename(project, version)}'

    @staticmethod
    def _validate_pointer(project: str, pointer: dict) -> None:
        if not isinstance(pointer, Mapping):
            raise MalformedPointerError(project, 'pointer')

        for key in REQUIRED_POINTER_KEYS:
            if key not in pointer:
                raise MalformedPointerError(project, key)

        digest = pointer['digest']
        if not isinstance(digest, str) or not SHA256_HEX_RE.match(digest):
            raise MalformedPointerError(project, 'digest')

        length = pointer['length']
        if not isinstance(length, int) or isinstance(length, bool) or length < 0:
            raise MalformedPointerError(project, 'length')

        wheel_path = pointer['wheel_path']
        if not isinstance(wheel_path, str) or not wheel_path.startswith('/') or wheel_path.startswith('//'):
            raise MalformedPointerError(project, 'wheel_path')
        normalized = posixpath.normpath(wheel_path)
        if normalized != wheel_path:
            raise MalformedPointerError(project, 'wheel_path')

    @staticmethod
    def _verify_content(project: str, content: bytes, pointer: dict) -> None:
        if len(content) != pointer['length']:
            raise LengthMismatch(project, pointer['length'], len(content))
        actual_digest = hashlib.sha256(content).hexdigest()
        if actual_digest != pointer['digest']:
            raise DigestMismatch(project, pointer['digest'], actual_digest)

    def get_pointer(self, project: str, version: str | None = None) -> dict:
        """Return the pointer JSON for *project* at *version* (or 'latest' when None)."""
        with tempfile.TemporaryDirectory() as tmp:
            metadata_dir = Path(tmp) / 'metadata'
            target_dir = Path(tmp) / 'targets'
            metadata_dir.mkdir()
            target_dir.mkdir()

            target_path = self._target_path(project, version)
            self._bootstrap_metadata_dir(metadata_dir)
            updater = self._make_updater(metadata_dir, target_dir)
            updater.refresh()

            target_info = updater.get_targetinfo(target_path)
            if target_info is None:
                label = version if version is not None else 'latest stable'
                raise TargetNotFoundError(f'No TUF target for {project!r} version {label!r}')

            pointer_path = target_dir / target_path
            pointer_path.parent.mkdir(parents=True, exist_ok=True)
            updater.download_target(target_info, pointer_path)

            return json.loads(pointer_path.read_text(encoding='utf-8'))

    def download(self, project: str, version: str | None = None, dest_dir: Path | None = None) -> Path:
        """Download and verify the wheel for *project* at *version*; return its path."""
        if self._disable_verification:
            if version is None:
                raise MissingVersion('unsafe-disable-verification requires an explicit --version')
            wheel_url = self._direct_wheel_url(project, version)
            wheel_filename = self._wheel_filename(project, version)
            pointer: dict | None = None
        else:
            pointer = self.get_pointer(project, version)
            self._validate_pointer(project, pointer)
            wheel_url = self._repository_url + pointer['wheel_path']
            wheel_filename = Path(pointer['wheel_path']).name

        dest = (dest_dir or Path(tempfile.mkdtemp())) / wheel_filename

        logger.info('Downloading wheel from %s', wheel_url)
        with urllib.request.urlopen(wheel_url, timeout=WHEEL_FETCH_TIMEOUT_SECONDS) as resp:
            content = resp.read()

        if pointer is not None:
            self._verify_content(project, content, pointer)

        dest.write_bytes(content)
        logger.info('Wrote %s to %s', wheel_filename, dest)
        return dest
