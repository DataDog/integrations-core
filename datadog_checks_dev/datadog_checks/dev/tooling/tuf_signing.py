# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
TUF (The Update Framework) signing utilities for integration wheels.

This module uses the python-tuf library to generate and sign TUF metadata
for pointer files, enabling secure distribution of integration wheels.
"""
import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from tuf.api.metadata import (
    Key,
    Metadata,
    MetaFile,
    Role,
    Root,
    Snapshot,
    Targets,
    TargetFile,
    Timestamp,
)
from tuf.api.serialization.json import JSONSerializer
from securesystemslib.signer import SSlibSigner


def generate_dummy_keys(keys_dir: Path) -> dict[str, dict]:
    """Generate Ed25519 keys for TUF roles (POC only).

    Creates dummy Ed25519 key pairs for root, targets, snapshot, and
    timestamp roles using the cryptography library. These are for POC
    purposes only and should NOT be used in production.

    Args:
        keys_dir: Directory to store generated keys

    Returns:
        Dictionary mapping role names to key dictionaries
    """
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    from securesystemslib.formats import encode_canonical

    roles = ['root', 'targets', 'snapshot', 'timestamp']
    keys = {}

    keys_dir.mkdir(parents=True, exist_ok=True)

    for role in roles:
        # Generate Ed25519 key pair using cryptography
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Extract raw bytes
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        # Convert to hex
        private_hex = private_bytes.hex()
        public_hex = public_bytes.hex()

        # Calculate keyid (SHA256 of canonical JSON of public key metadata)
        key_metadata = {
            'keytype': 'ed25519',
            'scheme': 'ed25519',
            'keyid_hash_algorithms': ['sha256', 'sha512'],
            'keyval': {'public': public_hex},
        }
        canonical = encode_canonical(key_metadata)
        keyid = hashlib.sha256(canonical.encode('utf-8')).hexdigest()

        # Create key dict in securesystemslib format (compatible with python-tuf)
        key_dict = {
            'keytype': 'ed25519',
            'scheme': 'ed25519',
            'keyid_hash_algorithms': ['sha256', 'sha512'],
            'keyid': keyid,
            'keyval': {
                'public': public_hex,
                'private': private_hex,
            },
        }

        # Save private key
        private_path = keys_dir / f'{role}_key'
        with open(private_path, 'w') as f:
            json.dump(key_dict, f, indent=2)

        # Save public key
        public_dict = {k: v for k, v in key_dict.items() if k != 'keyval'}
        public_dict['keyval'] = {'public': public_hex}
        public_path = keys_dir / f'{role}_key.pub'
        with open(public_path, 'w') as f:
            json.dump(public_dict, f, indent=2)

        keys[role] = key_dict

    return keys


def load_keys(keys_dir: Path) -> dict[str, dict]:
    """Load TUF keys from disk.

    Args:
        keys_dir: Directory containing key files

    Returns:
        Dictionary mapping role names to key dictionaries
    """
    roles = ['root', 'targets', 'snapshot', 'timestamp']
    keys = {}

    for role in roles:
        key_path = keys_dir / f'{role}_key'
        with open(key_path, 'r') as f:
            keys[role] = json.load(f)

    return keys


def generate_root_metadata(keys: dict[str, dict], expires_days: int = 365) -> Metadata[Root]:
    """Generate root.json metadata using python-tuf library.

    Args:
        keys: Dictionary mapping role names to key dictionaries
        expires_days: Number of days until expiration

    Returns:
        Metadata[Root] object (unsigned)
    """
    expires = datetime.now(timezone.utc) + timedelta(days=expires_days)

    # Convert securesystemslib keys to TUF Key objects
    # NOTE: Key.from_dict() modifies the dict, so we must use deep copies
    tuf_keys = {}
    for key_dict in keys.values():
        keyid = key_dict['keyid']
        key_dict_copy = copy.deepcopy(key_dict)
        key = Key.from_dict(keyid, key_dict_copy)
        tuf_keys[key.keyid] = key

    # Build roles
    roles = {}
    for role_name, key_dict in keys.items():
        keyid = key_dict['keyid']
        key_dict_copy = copy.deepcopy(key_dict)
        key = Key.from_dict(keyid, key_dict_copy)
        roles[role_name] = Role(keyids=[key.keyid], threshold=1)

    # Create Root object
    root = Root(
        version=1,
        spec_version='1.0.0',
        expires=expires,
        keys=tuf_keys,
        roles=roles,
        consistent_snapshot=False,
    )

    # Wrap in Metadata
    return Metadata[Root](signed=root, signatures={})


def generate_targets_metadata(
    s3_client, bucket: str, keys: dict[str, dict], expires_days: int = 365
) -> Metadata[Targets]:
    """Generate targets.json metadata using python-tuf library.

    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        keys: Dictionary mapping role names to key dictionaries
        expires_days: Number of days until expiration

    Returns:
        Metadata[Targets] object (unsigned)
    """
    expires = datetime.now(timezone.utc) + timedelta(days=expires_days)

    # Discover pointer files from S3
    targets_dict = {}

    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix='pointers/')

        if 'Contents' not in response:
            print("No pointer files found in S3")
            # Create empty targets
            targets = Targets(
                version=1,
                spec_version='1.0.0',
                expires=expires,
                targets={},
                delegations=None,
            )
            return Metadata[Targets](signed=targets, signatures={})

        for obj in response['Contents']:
            if not obj['Key'].endswith('.pointer'):
                continue

            # Download and parse pointer file
            pointer_data = s3_client.get_object(Bucket=bucket, Key=obj['Key'])
            pointer_bytes = pointer_data['Body'].read()

            try:
                pointer = yaml.safe_load(pointer_bytes)['pointer']
            except (yaml.YAMLError, KeyError) as e:
                print(f"Warning: Failed to parse pointer file {obj['Key']}: {e}")
                continue

            # Calculate hash of pointer file
            pointer_hash = hashlib.sha256(pointer_bytes).hexdigest()

            # Create TargetFile with custom metadata in unrecognized_fields
            target_file = TargetFile(
                length=len(pointer_bytes),
                hashes={'sha256': pointer_hash},
                path=obj['Key'],
                unrecognized_fields={
                    'custom': {
                        'package_name': pointer.get('name', ''),
                        'package_version': pointer.get('version', ''),
                        'wheel_uri': pointer.get('uri', ''),
                        'wheel_digest': pointer.get('digest', ''),
                    }
                },
            )

            targets_dict[obj['Key']] = target_file

    except Exception as e:
        print(f"Error listing pointer files from S3: {e}")
        raise

    # Create Targets object
    targets = Targets(
        version=1,
        spec_version='1.0.0',
        expires=expires,
        targets=targets_dict,
        delegations=None,
    )

    return Metadata[Targets](signed=targets, signatures={})


def generate_snapshot_metadata(targets_metadata: Metadata[Targets], expires_days: int = 30) -> Metadata[Snapshot]:
    """Generate snapshot.json metadata using python-tuf library.

    Args:
        targets_metadata: Signed targets metadata
        expires_days: Number of days until expiration

    Returns:
        Metadata[Snapshot] object (unsigned)
    """
    expires = datetime.now(timezone.utc) + timedelta(days=expires_days)

    # Serialize targets to bytes and calculate hash
    serializer = JSONSerializer()
    targets_bytes = targets_metadata.to_bytes(serializer)
    targets_hash = hashlib.sha256(targets_bytes).hexdigest()

    # Create MetaFile for targets.json
    meta = {
        'targets.json': MetaFile(
            version=targets_metadata.signed.version,
            length=len(targets_bytes),
            hashes={'sha256': targets_hash},
        )
    }

    # Create Snapshot object
    snapshot = Snapshot(
        version=1,
        spec_version='1.0.0',
        expires=expires,
        meta=meta,
    )

    return Metadata[Snapshot](signed=snapshot, signatures={})


def generate_timestamp_metadata(snapshot_metadata: Metadata[Snapshot], expires_days: int = 1) -> Metadata[Timestamp]:
    """Generate timestamp.json metadata using python-tuf library.

    Args:
        snapshot_metadata: Signed snapshot metadata
        expires_days: Number of days until expiration

    Returns:
        Metadata[Timestamp] object (unsigned)
    """
    expires = datetime.now(timezone.utc) + timedelta(days=expires_days)

    # Serialize snapshot to bytes and calculate hash
    serializer = JSONSerializer()
    snapshot_bytes = snapshot_metadata.to_bytes(serializer)
    snapshot_hash = hashlib.sha256(snapshot_bytes).hexdigest()

    # Create MetaFile for snapshot.json
    snapshot_meta = MetaFile(
        version=snapshot_metadata.signed.version,
        length=len(snapshot_bytes),
        hashes={'sha256': snapshot_hash},
    )

    # Create Timestamp object
    timestamp = Timestamp(
        version=1,
        spec_version='1.0.0',
        expires=expires,
        snapshot_meta=snapshot_meta,
    )

    return Metadata[Timestamp](signed=timestamp, signatures={})


def sign_metadata(metadata: Metadata, key_dict: dict) -> Metadata:
    """Sign metadata using python-tuf's signing mechanism.

    Args:
        metadata: Metadata object to sign
        key_dict: Key dictionary in securesystemslib format

    Returns:
        Signed metadata object
    """
    # Create signer from securesystemslib key
    signer = SSlibSigner(key_dict)

    # Sign the metadata (adds signature to metadata.signatures)
    metadata.sign(signer, append=True)

    return metadata


def generate_tuf_metadata(s3_client, bucket: str, keys: dict[str, dict], output_dir: Path) -> None:
    """Generate and upload TUF metadata using python-tuf library.

    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        keys: Dictionary mapping role names to key dictionaries
        output_dir: Local directory to save metadata files
    """
    serializer = JSONSerializer()
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate and sign root.json
    print("Generating root.json...")
    root_metadata = generate_root_metadata(keys, expires_days=365)
    root_metadata = sign_metadata(root_metadata, keys['root'])

    # Save locally
    root_path = output_dir / 'root.json'
    root_path.write_bytes(root_metadata.to_bytes(serializer))

    # Upload to S3 (both root.json and versioned)
    root_version = root_metadata.signed.version
    s3_client.upload_file(
        str(root_path), bucket, 'metadata/root.json', ExtraArgs={'ACL': 'public-read'}
    )
    s3_client.upload_file(
        str(root_path),
        bucket,
        f'metadata/{root_version}.root.json',
        ExtraArgs={'ACL': 'public-read'},
    )
    print(f"Uploaded root.json and {root_version}.root.json (public-read)")

    # 2. Generate and sign targets.json
    print("Generating targets.json...")
    targets_metadata = generate_targets_metadata(s3_client, bucket, keys, expires_days=365)
    targets_metadata = sign_metadata(targets_metadata, keys['targets'])

    targets_path = output_dir / 'targets.json'
    targets_path.write_bytes(targets_metadata.to_bytes(serializer))
    s3_client.upload_file(
        str(targets_path), bucket, 'metadata/targets.json', ExtraArgs={'ACL': 'public-read'}
    )
    print(f"Uploaded targets.json with {len(targets_metadata.signed.targets)} targets (public-read)")

    # 3. Generate and sign snapshot.json
    print("Generating snapshot.json...")
    snapshot_metadata = generate_snapshot_metadata(targets_metadata, expires_days=30)
    snapshot_metadata = sign_metadata(snapshot_metadata, keys['snapshot'])

    snapshot_path = output_dir / 'snapshot.json'
    snapshot_path.write_bytes(snapshot_metadata.to_bytes(serializer))
    s3_client.upload_file(
        str(snapshot_path), bucket, 'metadata/snapshot.json', ExtraArgs={'ACL': 'public-read'}
    )
    print("Uploaded snapshot.json (public-read)")

    # 4. Generate and sign timestamp.json
    print("Generating timestamp.json...")
    timestamp_metadata = generate_timestamp_metadata(snapshot_metadata, expires_days=1)
    timestamp_metadata = sign_metadata(timestamp_metadata, keys['timestamp'])

    timestamp_path = output_dir / 'timestamp.json'
    timestamp_path.write_bytes(timestamp_metadata.to_bytes(serializer))
    s3_client.upload_file(
        str(timestamp_path), bucket, 'metadata/timestamp.json', ExtraArgs={'ACL': 'public-read'}
    )
    print("Uploaded timestamp.json (public-read)")
