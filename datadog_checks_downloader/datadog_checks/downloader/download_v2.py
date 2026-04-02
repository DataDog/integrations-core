# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""TUF pointer-file downloader (v2 repository format).

The v2 format stores a JSON pointer file as a TUF target at:

    targets/<project>/<version>.json   (versioned)
    targets/<project>/latest.json      (latest stable, updated on each release)

Each pointer file contains:

    {
      "digest":           "<sha256 hex>",
      "length":           <int>,
      "version":          "<semver>",
      "repository":       "https://<bucket>.s3.amazonaws.com",
      "wheel_path":       "/wheels/<project>/<wheel>.whl",
      "attestation_path": "/attestations/<project>/<version>.sigstore.json"
    }

The downloader TUF-verifies the pointer file, then fetches the wheel from
``repository + wheel_path`` and verifies the sha256 digest and byte length
before writing to disk.
"""

import hashlib
import json
import logging
import shutil
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from tuf.ngclient import Updater

from .exceptions import DigestMismatch, TargetNotFoundError

logger = logging.getLogger(__name__)


class TUFPointerDownloader:
    """Downloads Datadog integration wheels from a v2 TUF repository."""

    def __init__(
        self,
        repository_url: str,
        trust_anchor: Path | None = None,
        verbose: int = 0,
        disable_verification: bool = False,
    ):
        """
        repository_url:       HTTPS base URL of the TUF repository, e.g.
                              'https://agent-integration-wheels-staging.s3.amazonaws.com'
        trust_anchor:         Path to the initial root.json that seeds the TUF
                              trust chain.  When None, root.json is fetched from
                              the repository on first use (TOFU — only safe in
                              controlled CI environments where the caller already
                              trusts the transport, e.g. via GitHub Actions OIDC).
        disable_verification: Skip TUF metadata verification and wheel digest
                              checks.  Use only as a break-glass escape hatch
                              (mirrors --unsafe-disable-verification in v1).
        """
        remainder = min(verbose, 5) % 6
        level = (6 - remainder) * 10
        logging.basicConfig(format='%(levelname)-8s: %(message)s', level=level)

        self._repository_url = repository_url.rstrip('/')
        self._trust_anchor = trust_anchor
        self._disable_verification = disable_verification

        if disable_verification:
            logger.warning(
                'Running with TUF verification disabled. '
                'Integrity is protected only by TLS (HTTPS).'
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _bootstrap_metadata_dir(self, metadata_dir: Path) -> None:
        """Seed *metadata_dir* with the initial root.json trust anchor."""
        dest = metadata_dir / 'root.json'
        if self._trust_anchor is not None:
            shutil.copy2(self._trust_anchor, dest)
        else:
            # TOFU: fetch the versioned initial root from the repository.
            url = f'{self._repository_url}/metadata/1.root.json'
            logger.debug('Fetching initial root from %s (TOFU)', url)
            with urllib.request.urlopen(url) as resp:
                dest.write_bytes(resp.read())

    def _make_updater(self, metadata_dir: Path, target_dir: Path) -> Updater:
        return Updater(
            metadata_dir=str(metadata_dir),
            metadata_base_url=f'{self._repository_url}/metadata/',
            target_base_url=f'{self._repository_url}/targets/',
            target_dir=str(target_dir),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_pointer(self, project: str, version: str | None = None) -> dict:
        """Return the TUF-verified pointer JSON for *project* at *version*.

        *version* = None resolves to ``latest.json`` (stable releases only).
        Raises ``TargetNotFoundError`` if the target is absent from the TUF repo.
        """
        target_path = f'{project}/{version or "latest"}.json'

        with tempfile.TemporaryDirectory() as tmp:
            metadata_dir = Path(tmp) / 'metadata'
            target_dir = Path(tmp) / 'targets'
            metadata_dir.mkdir()
            target_dir.mkdir()

            if self._disable_verification:
                url = f'{self._repository_url}/targets/{target_path}'
                try:
                    with urllib.request.urlopen(url) as resp:
                        return json.loads(resp.read())
                except urllib.error.HTTPError as exc:
                    if exc.code == 404:
                        raise TargetNotFoundError(
                            f'Pointer not found: {target_path}'
                        ) from exc
                    raise

            self._bootstrap_metadata_dir(metadata_dir)

            updater = self._make_updater(metadata_dir, target_dir)
            updater.refresh()

            target_info = updater.get_targetinfo(target_path)
            if target_info is None:
                raise TargetNotFoundError(
                    f'No TUF target for {project!r} version {version or "latest"!r}'
                )

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
        pointer = self.get_pointer(project, version)
        wheel_url = pointer['repository'] + pointer['wheel_path']
        wheel_filename = Path(pointer['wheel_path']).name
        dest = (dest_dir or Path(tempfile.mkdtemp())) / wheel_filename

        logger.info('Downloading wheel from %s', wheel_url)
        with urllib.request.urlopen(wheel_url) as resp:
            content = resp.read()

        if not self._disable_verification:
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
