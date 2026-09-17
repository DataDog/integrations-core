# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Synthetic TUF repository builder for v2 downloader tests."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer

from securesystemslib.keys import generate_ed25519_key
from securesystemslib.signer import SSlibKey, SSlibSigner
from tuf.api.metadata import (
    DelegatedRole,
    Delegations,
    Metadata,
    MetaFile,
    Role,
    Root,
    Snapshot,
    TargetFile,
    Targets,
    Timestamp,
)

SPEC_VERSION = '1.0.31'
EXPIRY = datetime(2099, 1, 1, tzinfo=timezone.utc)
TOP_LEVEL_ROLES = ('root', 'targets', 'snapshot', 'timestamp')


def _make_signers(role_names: tuple[str, ...]) -> tuple[dict[str, SSlibSigner], dict[str, SSlibKey]]:
    signers: dict[str, SSlibSigner] = {}
    public_keys: dict[str, SSlibKey] = {}
    for role in role_names:
        priv = generate_ed25519_key()
        signers[role] = SSlibSigner(priv)
        public_keys[role] = SSlibKey.from_securesystemslib_key(priv)
    return signers, public_keys


def _write_target_blob(targets_dir: Path, target_path: str, blob: bytes, hash_hex: str) -> None:
    dirname, _, basename = target_path.rpartition('/')
    hashed_basename = f'{hash_hex}.{basename}'
    on_disk_path = targets_dir / dirname / hashed_basename
    on_disk_path.parent.mkdir(parents=True, exist_ok=True)
    on_disk_path.write_bytes(blob)


def build_delegated_repo(
    root_dir: Path,
    delegated_targets: dict[str, bytes],
    delegated_role_name: str = 'pointers',
    paths: list[str] | None = None,
    path_hash_prefixes: list[str] | None = None,
) -> None:
    """Materialize a signed v2-style TUF repo with one delegated targets role."""
    if (paths is None) == (path_hash_prefixes is None):
        raise ValueError('exactly one of paths or path_hash_prefixes must be set')

    metadata_dir = root_dir / 'metadata'
    targets_dir = root_dir / 'targets'
    metadata_dir.mkdir(parents=True, exist_ok=True)
    targets_dir.mkdir(parents=True, exist_ok=True)

    signers, public_keys = _make_signers(TOP_LEVEL_ROLES + (delegated_role_name,))

    target_files: dict[str, TargetFile] = {}
    for target_path, blob in delegated_targets.items():
        tf = TargetFile.from_data(target_path, blob, hash_algorithms=['sha256'])
        target_files[target_path] = tf
        _write_target_blob(targets_dir, target_path, blob, next(iter(tf.hashes.values())))

    delegated_targets_md = Metadata(
        signed=Targets(version=1, spec_version=SPEC_VERSION, expires=EXPIRY, targets=target_files),
    )
    delegated_targets_md.sign(signers[delegated_role_name])
    delegated_targets_md.to_file(str(metadata_dir / f'1.{delegated_role_name}.json'))

    delegated_role = DelegatedRole(
        name=delegated_role_name,
        keyids=[public_keys[delegated_role_name].keyid],
        threshold=1,
        terminating=False,
        paths=paths,
        path_hash_prefixes=path_hash_prefixes,
    )
    delegations = Delegations(
        keys={public_keys[delegated_role_name].keyid: public_keys[delegated_role_name]},
        roles={delegated_role_name: delegated_role},
    )

    top_targets_md = Metadata(
        signed=Targets(version=1, spec_version=SPEC_VERSION, expires=EXPIRY, delegations=delegations),
    )
    top_targets_md.sign(signers['targets'])
    top_targets_md.to_file(str(metadata_dir / '1.targets.json'))

    snapshot_md = Metadata(
        signed=Snapshot(
            version=1,
            spec_version=SPEC_VERSION,
            expires=EXPIRY,
            meta={
                'targets.json': MetaFile(version=1),
                f'{delegated_role_name}.json': MetaFile(version=1),
            },
        ),
    )
    snapshot_md.sign(signers['snapshot'])
    snapshot_md.to_file(str(metadata_dir / '1.snapshot.json'))

    timestamp_md = Metadata(
        signed=Timestamp(version=1, spec_version=SPEC_VERSION, expires=EXPIRY, snapshot_meta=MetaFile(version=1)),
    )
    timestamp_md.sign(signers['timestamp'])
    timestamp_md.to_file(str(metadata_dir / 'timestamp.json'))

    roles = {name: Role(keyids=[public_keys[name].keyid], threshold=1) for name in TOP_LEVEL_ROLES}
    root_keys = {public_keys[name].keyid: public_keys[name] for name in TOP_LEVEL_ROLES}
    root_md = Metadata(
        signed=Root(
            version=1,
            spec_version=SPEC_VERSION,
            expires=EXPIRY,
            keys=root_keys,
            roles=roles,
            consistent_snapshot=True,
        ),
    )
    root_md.sign(signers['root'])
    root_md.to_file(str(metadata_dir / '1.root.json'))
    root_md.to_file(str(metadata_dir / 'root.json'))


class _ReuseTCPServer(TCPServer):
    allow_reuse_address = True


@contextmanager
def serve_directory(directory: Path) -> Iterator[str]:
    """Serve ``directory`` over HTTP for the duration of the context."""
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    with _ReuseTCPServer(('127.0.0.1', 0), handler) as httpd:
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield f'http://127.0.0.1:{port}'
        finally:
            httpd.shutdown()
            thread.join(timeout=2)
