# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
TUF (The Update Framework) signing utilities for integration wheels.

This module provides utilities to generate and sign TUF metadata for
pointer files, enabling secure distribution of integration wheels.
"""
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml


def generate_dummy_keys(keys_dir: Path) -> dict[str, dict]:
    """Generate Ed25519 keys for TUF roles (POC only).

    Creates dummy Ed25519 key pairs for root, targets, snapshot, and
    timestamp roles. These are for POC purposes only and should NOT
    be used in production.

    Args:
        keys_dir: Directory to store generated keys

    Returns:
        Dictionary mapping role names to public key dictionaries
    """
    from securesystemslib.keys import generate_ed25519_key
    from securesystemslib import interface

    roles = ['root', 'targets', 'snapshot', 'timestamp']
    keys = {}

    keys_dir.mkdir(parents=True, exist_ok=True)

    for role in roles:
        # Generate key
        key_dict = generate_ed25519_key()

        # Save private key with password
        private_key_path = keys_dir / f"{role}_key"
        with open(private_key_path, 'w') as f:
            json.dump(key_dict, f, indent=2)

        # Save public key
        public_key_path = keys_dir / f"{role}_key.pub"
        with open(public_key_path, 'w') as f:
            # Only save the public portion
            public_key = {
                'keytype': key_dict['keytype'],
                'scheme': key_dict['scheme'],
                'keyid': key_dict['keyid'],
                'keyid_hash_algorithms': key_dict['keyid_hash_algorithms'],
                'keyval': {'public': key_dict['keyval']['public']},
            }
            json.dump(public_key, f, indent=2)

        keys[role] = key_dict

        print(f"Generated {role} key: {key_dict['keyid'][:8]}...")

    return keys


def load_keys(keys_dir: Path) -> dict[str, dict]:
    """Load TUF keys from directory.

    Args:
        keys_dir: Directory containing key files

    Returns:
        Dictionary mapping role names to key dictionaries
    """
    roles = ['root', 'targets', 'snapshot', 'timestamp']
    keys = {}

    for role in roles:
        key_path = keys_dir / f"{role}_key"
        if not key_path.exists():
            raise FileNotFoundError(f"Key file not found: {key_path}")

        with open(key_path, 'r') as f:
            keys[role] = json.load(f)

    return keys


def sign_metadata_dict(metadata: dict[str, Any], key_dict: dict) -> dict[str, Any]:
    """Sign TUF metadata with given key.

    Args:
        metadata: Metadata dictionary with 'signed' key
        key_dict: Key dictionary with 'keyid' and 'keyval'

    Returns:
        Metadata dictionary with added signature
    """
    from securesystemslib.formats import encode_canonical
    from securesystemslib.keys import create_signature

    # Canonicalize the signed portion
    canonical_bytes = encode_canonical(metadata['signed']).encode('utf-8')

    # Create signature
    signature = create_signature(key_dict, canonical_bytes)

    # Add signature to metadata
    if 'signatures' not in metadata:
        metadata['signatures'] = []

    metadata['signatures'].append(signature)

    return metadata


def generate_root_metadata(keys: dict[str, dict], expires_days: int = 365) -> dict[str, Any]:
    """Generate root.json metadata.

    Args:
        keys: Dictionary mapping role names to key dictionaries
        expires_days: Number of days until expiration

    Returns:
        Root metadata dictionary (unsigned)
    """
    expires = datetime.utcnow() + timedelta(days=expires_days)

    # Build keys dict for root metadata
    keys_dict = {}
    for role, key_dict in keys.items():
        keys_dict[key_dict['keyid']] = {
            'keytype': key_dict['keytype'],
            'scheme': key_dict['scheme'],
            'keyid_hash_algorithms': key_dict['keyid_hash_algorithms'],
            'keyval': {'public': key_dict['keyval']['public']},
        }

    # Build roles dict
    roles = {}
    for role, key_dict in keys.items():
        roles[role] = {'keyids': [key_dict['keyid']], 'threshold': 1}

    root_metadata = {
        'signed': {
            '_type': 'root',
            'spec_version': '1.0.0',
            'version': 1,
            'expires': expires.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'keys': keys_dict,
            'roles': roles,
            'consistent_snapshot': False,
        },
        'signatures': [],
    }

    return root_metadata


def generate_targets_metadata(
    s3_client, bucket: str, keys: dict[str, dict], expires_days: int = 365
) -> dict[str, Any]:
    """Generate targets.json metadata from S3 pointer files.

    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name
        keys: Dictionary of TUF keys
        expires_days: Number of days until expiration

    Returns:
        Targets metadata dictionary (unsigned)
    """
    expires = datetime.utcnow() + timedelta(days=expires_days)
    targets = {}

    # List all pointer files in S3
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix='pointers/')

    for page in pages:
        if 'Contents' not in page:
            continue

        for obj in page['Contents']:
            key = obj['Key']
            if not key.endswith('.pointer'):
                continue

            # Download and parse pointer file
            try:
                response = s3_client.get_object(Bucket=bucket, Key=key)
                # Read body once (StreamingBody is not seekable)
                pointer_bytes = response['Body'].read()

                # Parse YAML from bytes
                pointer_content = yaml.safe_load(pointer_bytes)
                pointer = pointer_content.get('pointer', {})

                # Calculate hash of pointer file itself
                pointer_hash = hashlib.sha256(pointer_bytes).hexdigest()

                # Add to targets
                targets[key] = {
                    'length': len(pointer_bytes),
                    'hashes': {'sha256': pointer_hash},
                    'custom': {
                        'package_name': pointer.get('name', ''),
                        'package_version': pointer.get('version', ''),
                        'wheel_uri': pointer.get('uri', ''),
                        'wheel_digest': pointer.get('digest', ''),
                    },
                }

                print(f"Added target: {key}")

            except Exception as e:
                print(f"Warning: Failed to process pointer file {key}: {e}")
                continue

    targets_metadata = {
        'signed': {
            '_type': 'targets',
            'spec_version': '1.0.0',
            'version': 1,
            'expires': expires.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'targets': targets,
            'delegations': {},
        },
        'signatures': [],
    }

    return targets_metadata


def generate_snapshot_metadata(targets_metadata: dict[str, Any], expires_days: int = 30) -> dict[str, Any]:
    """Generate snapshot.json metadata.

    Args:
        targets_metadata: Signed targets metadata
        expires_days: Number of days until expiration

    Returns:
        Snapshot metadata dictionary (unsigned)
    """
    expires = datetime.utcnow() + timedelta(days=expires_days)

    # Calculate hash and length of targets.json
    targets_bytes = json.dumps(targets_metadata, indent=2, sort_keys=True).encode('utf-8')
    targets_hash = hashlib.sha256(targets_bytes).hexdigest()

    snapshot_metadata = {
        'signed': {
            '_type': 'snapshot',
            'spec_version': '1.0.0',
            'version': 1,
            'expires': expires.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'meta': {
                'targets.json': {
                    'version': targets_metadata['signed']['version'],
                    'length': len(targets_bytes),
                    'hashes': {'sha256': targets_hash},
                }
            },
        },
        'signatures': [],
    }

    return snapshot_metadata


def generate_timestamp_metadata(snapshot_metadata: dict[str, Any], expires_days: int = 1) -> dict[str, Any]:
    """Generate timestamp.json metadata.

    Args:
        snapshot_metadata: Signed snapshot metadata
        expires_days: Number of days until expiration (typically 1 day)

    Returns:
        Timestamp metadata dictionary (unsigned)
    """
    expires = datetime.utcnow() + timedelta(days=expires_days)

    # Calculate hash and length of snapshot.json
    snapshot_bytes = json.dumps(snapshot_metadata, indent=2, sort_keys=True).encode('utf-8')
    snapshot_hash = hashlib.sha256(snapshot_bytes).hexdigest()

    timestamp_metadata = {
        'signed': {
            '_type': 'timestamp',
            'spec_version': '1.0.0',
            'version': 1,
            'expires': expires.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'meta': {
                'snapshot.json': {
                    'version': snapshot_metadata['signed']['version'],
                    'length': len(snapshot_bytes),
                    'hashes': {'sha256': snapshot_hash},
                }
            },
        },
        'signatures': [],
    }

    return timestamp_metadata


def generate_tuf_metadata(s3_client, bucket: str, keys: dict[str, dict], output_dir: Path) -> None:
    """Generate complete TUF metadata from S3 pointer files.

    This function orchestrates the generation of all TUF metadata files:
    1. Generates root.json (defines keys and roles)
    2. Generates targets.json (lists pointer files)
    3. Generates snapshot.json (references targets.json)
    4. Generates timestamp.json (references snapshot.json)

    All metadata is signed with the appropriate keys and uploaded to S3.

    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name
        keys: Dictionary mapping role names to key dictionaries
        output_dir: Local directory to save metadata files

    Returns:
        None (uploads metadata to S3)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate and sign root.json
    print("Generating root.json...")
    root_metadata = generate_root_metadata(keys, expires_days=365)
    root_metadata = sign_metadata_dict(root_metadata, keys['root'])

    root_path = output_dir / 'root.json'
    with open(root_path, 'w') as f:
        json.dump(root_metadata, f, indent=2, sort_keys=True)

    s3_client.upload_file(str(root_path), bucket, 'metadata/root.json')
    print(f"Uploaded root.json")

    # 2. Generate and sign targets.json
    print("Generating targets.json...")
    targets_metadata = generate_targets_metadata(s3_client, bucket, keys, expires_days=365)
    targets_metadata = sign_metadata_dict(targets_metadata, keys['targets'])

    targets_path = output_dir / 'targets.json'
    with open(targets_path, 'w') as f:
        json.dump(targets_metadata, f, indent=2, sort_keys=True)

    s3_client.upload_file(str(targets_path), bucket, 'metadata/targets.json')
    print(f"Uploaded targets.json with {len(targets_metadata['signed']['targets'])} targets")

    # 3. Generate and sign snapshot.json
    print("Generating snapshot.json...")
    snapshot_metadata = generate_snapshot_metadata(targets_metadata, expires_days=30)
    snapshot_metadata = sign_metadata_dict(snapshot_metadata, keys['snapshot'])

    snapshot_path = output_dir / 'snapshot.json'
    with open(snapshot_path, 'w') as f:
        json.dump(snapshot_metadata, f, indent=2, sort_keys=True)

    s3_client.upload_file(str(snapshot_path), bucket, 'metadata/snapshot.json')
    print(f"Uploaded snapshot.json")

    # 4. Generate and sign timestamp.json
    print("Generating timestamp.json...")
    timestamp_metadata = generate_timestamp_metadata(snapshot_metadata, expires_days=1)
    timestamp_metadata = sign_metadata_dict(timestamp_metadata, keys['timestamp'])

    timestamp_path = output_dir / 'timestamp.json'
    with open(timestamp_path, 'w') as f:
        json.dump(timestamp_metadata, f, indent=2, sort_keys=True)

    s3_client.upload_file(str(timestamp_path), bucket, 'metadata/timestamp.json')
    print(f"Uploaded timestamp.json")

    print(f"\nTUF metadata generated successfully!")
    print(f"Local files: {output_dir}")
    print(f"S3 location: s3://{bucket}/metadata/")
