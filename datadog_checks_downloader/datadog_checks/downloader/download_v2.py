# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""TUF pointer-file downloader for the v2 repository format.

The downloader TUF-verifies a JSON pointer target, downloads the referenced
wheel, and verifies the wheel digest and byte length before writing it to disk.
"""

import hashlib
import importlib.resources
import json
import logging
import tempfile
import urllib.request
from pathlib import Path

from tuf.ngclient import Updater
from tuf.ngclient.config import UpdaterConfig

from .exceptions import DigestMismatch, TargetNotFoundError

logger = logging.getLogger(__name__)

V2_REPOSITORY_URL = "https://agent-integration-wheels-prod.s3.amazonaws.com"


class TUFPointerDownloader:
    """Downloads Datadog integration wheels from a v2 TUF repository."""

    def __init__(
        self,
        repository_url: str,
        verbose: int = 0,
        disable_verification: bool = False,
    ):
        """
        repository_url:       HTTPS base URL of the TUF repository, e.g.
                              'https://agent-integration-wheels-staging.s3.amazonaws.com'
        disable_verification: Skip TUF metadata verification and wheel digest
                              checks.  Use only as a break-glass escape hatch
                              (mirrors --unsafe-disable-verification in v1).
        """
        remainder = min(verbose, 5) % 6
        level = (6 - remainder) * 10
        logging.basicConfig(format='%(levelname)-8s: %(message)s', level=level)

        self._repository_url = repository_url.rstrip('/')
        self._disable_verification = disable_verification

        if disable_verification:
            logger.warning('Running with TUF verification disabled. Integrity is protected only by TLS (HTTPS).')

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _bootstrap_metadata_dir(self, metadata_dir: Path) -> None:
        """Seed *metadata_dir* with the bundled initial root.json trust anchor."""
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
        return f'{project}/{name}.json'

    @staticmethod
    def _wheel_filename(project: str, version: str) -> str:
        distribution = project.replace('-', '_')
        return f'{distribution}-{version}-py3-none-any.whl'

    def _direct_wheel_url(self, project: str, version: str) -> str:
        return f'{self._repository_url}/wheels/{project}/{self._wheel_filename(project, version)}'

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_pointer(self, project: str, version: str | None = None) -> dict:
        """Return the pointer JSON for *project* at *version*.

        Resolves *version* = None by fetching ``<project>/latest.json``.
        Raises ``TargetNotFoundError`` if the target is absent from the TUF repo.
        """
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

    def download(
        self,
        project: str,
        version: str | None = None,
        dest_dir: Path | None = None,
    ) -> Path:
        """Download and sha256-verify the wheel for *project* at *version*.

        Returns the absolute path to the downloaded ``.whl`` file.
        Raises ``DigestMismatch`` if the wheel digest or length does not match
        the pointer file.
        """
        if self._disable_verification:
            if version is None:
                raise TargetNotFoundError('unsafe-disable-verification requires an explicit --version')
            wheel_url = self._direct_wheel_url(project, version)
            wheel_filename = self._wheel_filename(project, version)
            pointer = None
        else:
            pointer = self.get_pointer(project, version)
            # Use the caller-supplied repository URL for the wheel fetch so that
            # --repository can point at a staging bucket and override the prod URL
            # baked into the pointer file.  This allows pre-promotion validation
            # against staging S3 without modifying pointer content.
            wheel_url = self._repository_url + pointer['wheel_path']
            wheel_filename = Path(pointer['wheel_path']).name

        dest = (dest_dir or Path(tempfile.mkdtemp())) / wheel_filename

        logger.info('Downloading wheel from %s', wheel_url)
        with urllib.request.urlopen(wheel_url) as resp:
            content = resp.read()

        if pointer is not None:
            actual_digest = hashlib.sha256(content).hexdigest()
            if actual_digest != pointer['digest']:
                raise DigestMismatch(project, pointer['digest'], actual_digest)
            if len(content) != pointer['length']:
                raise DigestMismatch(
                    project,
                    f'length={pointer["length"]}',
                    f'length={len(content)}',
                )

        dest.write_bytes(content)
        logger.info('Wrote %s to %s', wheel_filename, dest)
        return dest
