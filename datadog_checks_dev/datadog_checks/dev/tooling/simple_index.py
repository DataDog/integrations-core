# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Generate PEP 503 compliant simple indexes for integration wheels.

This module provides utilities to generate PyPI-compatible simple indexes
without downloading wheel files, achieving constant complexity by using
S3 metadata.
"""
import html
from typing import Any


def normalize_package_name(name: str) -> str:
    """Normalize package name according to PEP 503.

    Args:
        name: Package name (e.g., 'datadog-postgres')

    Returns:
        Normalized name with underscores and hyphens converted to hyphens
        and lowercased (e.g., 'datadog-postgres')
    """
    return name.lower().replace('_', '-')


def build_index_html(package_name: str, files: list[dict[str, Any]]) -> str:
    """Build PEP 503 compliant HTML index for a package.

    Args:
        package_name: Normalized package name
        files: List of dicts with keys: 'name', 'hash', 'size'

    Returns:
        HTML string for the package index
    """
    escaped_name = html.escape(package_name)
    links = []

    for file_info in sorted(files, key=lambda x: x['name']):
        file_name = html.escape(file_info['name'])
        file_hash = file_info.get('hash', '')

        # PEP 503 format: <a href="filename#sha256=hash">filename</a>
        if file_hash:
            link = f'<a href="{file_name}#sha256={file_hash}">{file_name}</a><br/>'
        else:
            link = f'<a href="{file_name}">{file_name}</a><br/>'

        links.append(link)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta name="pypi:repository-version" content="1.0">
<title>Links for {escaped_name}</title>
</head>
<body>
<h1>Links for {escaped_name}</h1>
{''.join(links)}
</body>
</html>"""

    return html_content


def build_root_index_html(packages: list[str]) -> str:
    """Build root index.html listing all packages.

    Args:
        packages: List of normalized package names

    Returns:
        HTML string for the root index
    """
    links = []

    for package in sorted(packages):
        escaped_package = html.escape(package)
        link = f'<a href="{escaped_package}/">{escaped_package}</a><br/>'
        links.append(link)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta name="pypi:repository-version" content="1.0">
<title>Simple Index</title>
</head>
<body>
<h1>Simple Index</h1>
{''.join(links)}
</body>
</html>"""

    return html_content


def generate_package_index(s3_client, bucket: str, package_name: str, use_pointers: bool = True) -> None:
    """Generate PEP 503 index for a package using S3 metadata.

    This function lists all wheel files for a package in S3, extracts
    their SHA256 hashes from S3 object metadata, and generates an
    index.html file without downloading the wheels.

    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name
        package_name: Package name (will be normalized)
        use_pointers: If True, generate index from pointer files (future use)

    Returns:
        None (uploads index.html to S3)
    """
    normalized_name = normalize_package_name(package_name)
    prefix = f"simple/{normalized_name}/"

    # List all objects in the package directory
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    files = []
    for page in pages:
        if 'Contents' not in page:
            continue

        for obj in page['Contents']:
            key = obj['Key']
            # Skip the index.html itself
            if key.endswith('index.html'):
                continue
            # Skip directories
            if key.endswith('/'):
                continue

            file_name = key.split('/')[-1]

            # Get object metadata to extract SHA256 hash
            try:
                head = s3_client.head_object(Bucket=bucket, Key=key)
                file_hash = head.get('Metadata', {}).get('sha256', '')
            except Exception:
                # If we can't get metadata, proceed without hash
                file_hash = ''

            files.append({
                'name': file_name,
                'hash': file_hash,
                'size': obj['Size'],
            })

    # Generate HTML index
    index_html = build_index_html(normalized_name, files)

    # Upload to S3
    index_key = f"{prefix}index.html"
    s3_client.put_object(
        Bucket=bucket,
        Key=index_key,
        Body=index_html.encode('utf-8'),
        ContentType='text/html',
        CacheControl='public, max-age=600',  # Cache for 10 minutes
        ACL='public-read',
    )

    print(f"Updated index for {normalized_name} at s3://{bucket}/{index_key}")


def generate_root_index(s3_client, bucket: str) -> None:
    """Generate root index.html listing all packages.

    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name

    Returns:
        None (uploads index.html to S3)
    """
    prefix = "simple/"

    # List all "directories" (common prefixes) under simple/
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter='/')

    packages = set()
    for page in pages:
        if 'CommonPrefixes' in page:
            for common_prefix in page['CommonPrefixes']:
                # Extract package name from prefix like "simple/datadog-postgres/"
                package = common_prefix['Prefix'].rstrip('/').split('/')[-1]
                packages.add(package)

    # Generate HTML index
    index_html = build_root_index_html(sorted(packages))

    # Upload to S3
    index_key = f"{prefix}index.html"
    s3_client.put_object(
        Bucket=bucket,
        Key=index_key,
        Body=index_html.encode('utf-8'),
        ContentType='text/html',
        CacheControl='public, max-age=600',
        ACL='public-read',
    )

    print(f"Updated root index at s3://{bucket}/{index_key}")
