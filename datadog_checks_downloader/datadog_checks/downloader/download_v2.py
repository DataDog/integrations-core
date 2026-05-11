# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""TUF pointer-file downloader (v2 repository format).

The v2 format stores a JSON pointer file as a TUF target at:

    targets/<project>/<version>.json   (versioned pointer)

Target files are content-addressed on S3 (consistent-snapshot format):
the actual file at ``targets/<project>/<version>.json`` is stored as
``targets/<project>/{sha256}.{version}.json``.  The TUF Updater resolves
the hash-prefixed path automatically via ``N.targets.json`` metadata.

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
import importlib.resources
import json
import logging
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from packaging.version import InvalidVersion, Version
from tuf.api.metadata import Metadata, Snapshot, Targets, Timestamp
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
            logger.warning(
                'Running with TUF verification disabled. '
                'Integrity is protected only by TLS (HTTPS).'
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _bootstrap_metadata_dir(self, metadata_dir: Path) -> None:
        """Seed *metadata_dir* with the bundled initial root.json trust anchor."""
        dest = metadata_dir / 'root.json'
        pkg = importlib.resources.files('datadog_checks.downloader')
        dest.write_bytes((pkg / '1.root.json').read_bytes())

    def _make_updater(self, metadata_dir: Path, target_dir: Path) -> Updater:
        return Updater(
            metadata_dir=str(metadata_dir),
            metadata_base_url=f'{self._repository_url}/metadata/',
            target_base_url=f'{self._repository_url}/targets/',
            target_dir=str(target_dir),
            config=UpdaterConfig(prefix_targets_with_hash=True),
        )

    @staticmethod
    def _resolve_version(project: str, version: str | None, targets: Targets) -> str:
        """Return the concrete version to fetch.

        If *version* is given, return it as-is (TUF will raise if absent).
        If None, scan *targets* for all ``<project>/<ver>.json`` entries and
        return the highest stable PEP 440 version.
        """
        if version is not None:
            return version

        prefix = f"{project}/"
        stable: list[Version] = []
        for target_path in targets.targets:
            if not (target_path.startswith(prefix) and target_path.endswith(".json")):
                continue
            stem = target_path[len(prefix): -len(".json")]
            try:
                v = Version(stem)
            except InvalidVersion:
                continue
            if not v.is_prerelease:
                stable.append(v)

        if not stable:
            raise TargetNotFoundError(f"No stable releases found for {project!r} in targets metadata")
        return str(max(stable))

    def _fetch_targets_unverified(self) -> Targets:
        """Fetch targets metadata without verifying TUF signatures.

        Walks timestamp → snapshot → targets to resolve the current versioned
        targets file and returns the parsed Targets signed payload.
        """
        base = self._repository_url

        with urllib.request.urlopen(f'{base}/metadata/timestamp.json') as r:
            ts: Metadata[Timestamp] = Metadata[Timestamp].from_bytes(r.read())
        snap_ver = ts.signed.snapshot_meta.version

        with urllib.request.urlopen(f'{base}/metadata/{snap_ver}.snapshot.json') as r:
            snap: Metadata[Snapshot] = Metadata[Snapshot].from_bytes(r.read())
        tgt_ver = snap.signed.meta['targets.json'].version

        with urllib.request.urlopen(f'{base}/metadata/{tgt_ver}.targets.json') as r:
            return Metadata[Targets].from_bytes(r.read()).signed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_pointer(self, project: str, version: str | None = None) -> dict:
        """Return the pointer JSON for *project* at *version*.

        Resolves *version* = None to the latest stable release by scanning
        ``N.targets.json``.  The pointer file is fetched via its hash-prefixed
        consistent-snapshot path.
        Raises ``TargetNotFoundError`` if the target is absent from the TUF repo.
        """
        with tempfile.TemporaryDirectory() as tmp:
            metadata_dir = Path(tmp) / 'metadata'
            target_dir = Path(tmp) / 'targets'
            metadata_dir.mkdir()
            target_dir.mkdir()

            if self._disable_verification:
                targets = self._fetch_targets_unverified()
                resolved = self._resolve_version(project, version, targets)
                target_path = f'{project}/{resolved}.json'

                entry = targets.targets.get(target_path)
                if entry is None:
                    raise TargetNotFoundError(f'Target not found: {target_path}')

                sha256 = entry.hashes.get('sha256', '')
                url = f'{self._repository_url}/targets/{project}/{sha256}.{resolved}.json'
                try:
                    with urllib.request.urlopen(url) as resp:
                        return json.loads(resp.read())
                except urllib.error.HTTPError as exc:
                    if exc.code == 404:
                        raise TargetNotFoundError(f'Pointer not found: {url}') from exc
                    raise

            self._bootstrap_metadata_dir(metadata_dir)
            updater = self._make_updater(metadata_dir, target_dir)
            updater.refresh()

            # Parse the downloaded N.targets.json to resolve version and
            # enumerate the hash-prefixed path the Updater will fetch.
            candidates = sorted(metadata_dir.glob('*.targets.json'))
            if not candidates:
                raise TargetNotFoundError(f'No targets metadata after refresh for {project!r}')
            targets = Metadata[Targets].from_file(str(candidates[-1])).signed

            resolved = self._resolve_version(project, version, targets)
            target_path = f'{project}/{resolved}.json'

            target_info = updater.get_targetinfo(target_path)
            if target_info is None:
                raise TargetNotFoundError(f'No TUF target for {project!r} version {resolved!r}')

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
