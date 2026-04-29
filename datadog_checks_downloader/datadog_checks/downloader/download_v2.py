# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""TUF pointer-file downloader (v2 repository format).

The v2 format stores a JSON pointer file as a TUF target at:

    targets/<project>/<version>.json

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

Latest-version resolution
-------------------------

When ``version`` is omitted, the downloader lists the bucket prefix
``targets/<project>/`` directly via S3's ``ListObjectsV2`` REST API,
filters keys to PEP 440 stable versions, and picks the maximum.  The
chosen version is then fetched through TUF as usual, so the pointer file
the client trusts is still cryptographically verified.

Why list S3 instead of parsing the signed targets metadata: once
``path_hash_prefixes`` delegations are in use in the TUF repo, the client
cannot tell from the metadata alone which delegation signs the latest
version of a given project.  A bucket listing sidesteps that — TUF still
authoritatively verifies whichever version is then requested.
"""

import hashlib
import json
import logging
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from packaging.version import InvalidVersion, Version
from tuf.ngclient import Updater

from .exceptions import DigestMismatch, TargetNotFoundError

logger = logging.getLogger(__name__)

# S3 ListObjectsV2 returns at most 1000 keys per request; pagination
# continues via the ``NextContinuationToken`` in the response.  Constant is
# the AWS-imposed max, included for clarity in the URL builder below.
_S3_MAX_KEYS = 1000

# All ListBucketResult elements live under this namespace.  Without a
# namespace prefix in the XPath, ``ElementTree.find`` won't match them.
_S3_NS = {'s3': 'http://s3.amazonaws.com/doc/2006-03-01/'}


def _is_stable(version_str: str) -> bool:
    """Return True if *version_str* is a stable PEP 440 release.

    Stable means: parses as PEP 440, not a pre-release (aN/bN/rcN), not a
    dev release (.devN), and no local-version identifier (+local).
    Post-releases count as stable.  Mirrors the publisher's definition so
    the two sides agree on what "stable" means.
    """
    try:
        v = Version(version_str)
    except InvalidVersion:
        return False
    if v.is_prerelease or v.is_devrelease:
        return False
    return v.local is None


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
            logger.warning('Running with TUF verification disabled. Integrity is protected only by TLS (HTTPS).')

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

    def _list_s3_keys(self, prefix: str) -> list[str]:
        """List every key under *prefix* in the public S3 bucket.

        Uses S3's ListObjectsV2 REST API directly so we don't depend on
        boto3.  Handles pagination via ``ContinuationToken``; returns all
        keys under the prefix in arbitrary order (caller filters).

        Raises ``TargetNotFoundError`` on HTTP 404 — that's how a missing
        project surfaces (S3 returns the bucket but with KeyCount=0, but a
        wholly unreachable bucket returns 404 / 403).
        """
        keys: list[str] = []
        continuation_token: str | None = None
        while True:
            params = {
                'list-type': '2',
                'prefix': prefix,
                'max-keys': str(_S3_MAX_KEYS),
            }
            if continuation_token is not None:
                params['continuation-token'] = continuation_token
            url = f'{self._repository_url}/?{urllib.parse.urlencode(params)}'
            try:
                with urllib.request.urlopen(url) as resp:
                    body = resp.read()
            except urllib.error.HTTPError as exc:
                raise TargetNotFoundError(f'Cannot list {prefix} (HTTP {exc.code})') from exc

            root = ET.fromstring(body)
            for content in root.findall('s3:Contents', _S3_NS):
                key_elem = content.find('s3:Key', _S3_NS)
                if key_elem is not None and key_elem.text:
                    keys.append(key_elem.text)

            truncated_elem = root.find('s3:IsTruncated', _S3_NS)
            if truncated_elem is None or truncated_elem.text != 'true':
                break
            token_elem = root.find('s3:NextContinuationToken', _S3_NS)
            if token_elem is None or not token_elem.text:
                # Truncated but no continuation token — treat as terminal
                # rather than loop forever.  S3 should never produce this
                # combination, but guard anyway.
                break
            continuation_token = token_elem.text
        return keys

    def _resolve_latest_version(self, project: str) -> str:
        """List the bucket and return the highest PEP 440 stable version
        for *project*.

        Raises ``TargetNotFoundError`` if no stable version is published.
        """
        prefix = f'targets/{project}/'
        keys = self._list_s3_keys(prefix)

        # Each key under the prefix is ``targets/<project>/<version>.json``.
        # Strip the prefix and the ``.json`` suffix to recover the version
        # string, then filter to keys that look like ``<version>.json``
        # (no further path segments — defensive against future siblings
        # under ``targets/<project>/`` that aren't pointer files).
        candidates: list[Version] = []
        for key in keys:
            tail = key[len(prefix) :]
            if '/' in tail or not tail.endswith('.json'):
                continue
            version_str = tail[: -len('.json')]
            if not _is_stable(version_str):
                continue
            try:
                candidates.append(Version(version_str))
            except InvalidVersion:
                continue

        if not candidates:
            raise TargetNotFoundError(f'No stable version found under s3 prefix {prefix!r}')
        return str(max(candidates))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_pointer(self, project: str, version: str | None = None) -> dict:
        """Return the TUF-verified pointer JSON for *project* at *version*.

        *version* = None resolves to the highest PEP 440 stable version
        published under ``targets/<project>/`` in the bucket.  The chosen
        version is then fetched through TUF, so the returned pointer is
        still cryptographically verified.

        Raises ``TargetNotFoundError`` if the target is absent from TUF or
        no stable version is published.
        """
        if version is None:
            version = self._resolve_latest_version(project)

        target_path = f'{project}/{version}.json'

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
                        raise TargetNotFoundError(f'Pointer not found: {target_path}') from exc
                    raise

            self._bootstrap_metadata_dir(metadata_dir)

            updater = self._make_updater(metadata_dir, target_dir)
            updater.refresh()

            target_info = updater.get_targetinfo(target_path)
            if target_info is None:
                raise TargetNotFoundError(f'No TUF target for {project!r} version {version!r}')

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
