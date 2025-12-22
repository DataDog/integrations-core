# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
import sys

from datadog_checks.dev.errors import ManifestError
from datadog_checks.dev.fs import (
    chdir,
    file_exists,
    path_join,
    read_file,
    read_file_lines,
    write_file,
    write_file_lines,
)
from datadog_checks.dev.subprocess import run_command

from .utils import get_version_file, load_manifest

# Maps the Python platform strings to the ones we have in the manifest
PLATFORMS_TO_PY = {"windows": "win32", "mac_os": "darwin", "linux": "linux2"}
ALL_PLATFORMS = sorted(PLATFORMS_TO_PY)
VERSION = re.compile(r'__version__ *= *(?:[\'"])(.+?)(?:[\'"])')
DATADOG_PACKAGE_PREFIX = "datadog-"


def get_release_tag_string(check_name, version_string):
    """
    Compose a string to use for release tags
    """
    if check_name == "ddev":
        version_string = f"v{version_string}"

    if check_name:
        return f"{check_name}-{version_string}"
    else:
        return version_string


def update_version_module(check_name, old_ver, new_ver):
    """
    Change the Python code in the __about__.py module so that `__version__`
    contains the new value.
    """
    version_file = get_version_file(check_name)
    contents = read_file(version_file)

    contents = contents.replace(old_ver, new_ver)
    write_file(version_file, contents)


def get_package_name(folder_name):
    """
    Given a folder name for a check, return the name of the
    corresponding Python package
    """
    if folder_name == "datadog_checks_base":
        return "datadog-checks-base"
    elif folder_name == "datadog_checks_downloader":
        return "datadog-checks-downloader"
    elif folder_name == "datadog_checks_dependency_provider":
        return "datadog-checks-dependency-provider"
    elif folder_name == "ddev":
        return "ddev"

    return f"{DATADOG_PACKAGE_PREFIX}{folder_name.replace('_', '-')}"


def get_folder_name(package_name):
    """
    Given a Python package name for a check, return the corresponding folder
    name in the git repo
    """
    if package_name == "datadog-checks-base":
        return "datadog_checks_base"
    elif package_name == "datadog-checks-downloader":
        return "datadog_checks_downloader"
    elif package_name == "datadog-checks-dependency-provider":
        return "datadog_checks_dependency_provider"
    elif package_name == "ddev":
        return "ddev"

    return package_name.replace("-", "_")[len(DATADOG_PACKAGE_PREFIX) :]


def get_agent_requirement_line(check, version):
    """
    Compose a text line to be used in a requirements.txt file to install a check
    pinned to a specific version.
    """
    package_name = get_package_name(check)

    # no manifest
    if check in (
        "datadog_checks_base",
        "datadog_checks_downloader",
        "datadog_checks_dependency_provider",
        "ddev",
    ):
        return f"{package_name}=={version}"

    m = load_manifest(check)
    if "tile" in m:
        platforms = []
        for classifier_tag in m["tile"]["classifier_tags"]:
            key, value = classifier_tag.split("::", 1)
            if key != "Supported OS":
                continue
            elif value == "macOS":
                value = "mac_os"
            platforms.append(value.lower())
        platforms.sort()
    else:
        platforms = sorted(m.get("supported_os", []))

    # all platforms
    if platforms == ALL_PLATFORMS:
        return f"{package_name}=={version}"
    # one specific platform
    elif len(platforms) == 1:
        return f"{package_name}=={version}; sys_platform == '{PLATFORMS_TO_PY.get(platforms[0])}'"
    elif platforms:
        if "windows" not in platforms:
            return f"{package_name}=={version}; sys_platform != 'win32'"
        elif "mac_os" not in platforms:
            return f"{package_name}=={version}; sys_platform != 'darwin'"
        elif "linux" not in platforms:
            return f"{package_name}=={version}; sys_platform != 'linux2'"

    raise ManifestError(
        f"Can't parse the supported OS list for the check {check}: {platforms}"
    )


def update_agent_requirements(req_file, check, newline):
    """
    Update the requirements lines for the given check
    """
    package_name = get_package_name(check)
    lines = read_file_lines(req_file)

    pkg_lines = {line.split("==")[0]: line for line in lines}
    pkg_lines[package_name] = f"{newline}\n"

    write_file_lines(req_file, sorted(pkg_lines.values()))


def build_package(package_path, sdist):
    with chdir(package_path):
        if file_exists(path_join(package_path, "pyproject.toml")):
            command = [sys.executable, "-m", "build"]
            if not sdist:
                command.append("--wheel")

            result = run_command(command, capture="out")
            if result.code != 0:
                return result
        else:
            # Clean up: Files built previously and now deleted might still persist in build directory
            # and will be included in the final wheel. Cleaning up before avoids that.
            result = run_command(
                [sys.executable, "setup.py", "clean", "--all"], capture="out"
            )
            if result.code != 0:
                return result

            result = run_command(
                [sys.executable, "setup.py", "bdist_wheel", "--universal"],
                capture="out",
            )
            if result.code != 0:
                return result

            if sdist:
                result = run_command(
                    [sys.executable, "setup.py", "sdist"], capture="out"
                )
                if result.code != 0:
                    return result
        # Create pointer artifact in JSON/yaml format for TUF
        # uri:
        # digest:
        import glob
        import hashlib
        import json
        import os
        from datetime import datetime, timezone

        import yaml

        # Get the most recent file in the dist directory
        list_of_wheels = glob.glob(os.path.join(package_path, "dist", "*"))
        wheel_path = max(list_of_wheels, key=os.path.getctime)
        URI_TEMPLATE = "https://test-public-integration-wheels.s3.eu-north-1.amazonaws.com/simple/{}/{}"
        ATTESTATION_URI_TEMPLATE = "https://test-public-integration-wheels.s3.eu-north-1.amazonaws.com/attestations/{}/{}"
        folder_name = os.path.basename(package_path)
        package_name = get_package_name(folder_name)
        wheel_name = os.path.basename(wheel_path)
        version = wheel_name.split("-")[1]
        uri = URI_TEMPLATE.format(package_name, wheel_name)
        print("Using URI: ", uri)
        with open(wheel_path, "rb") as wheel:
            digest = hashlib.sha256(wheel.read()).hexdigest()
        wheel_size = os.path.getsize(wheel_path)
        print("Using digest: ", digest)

        # Generate SLSA 2 provenance attestation
        attestation = {
            "_type": "https://in-toto.io/Statement/v0.1",
            "predicateType": "https://slsa.dev/provenance/v0.2",
            "subject": [
                {
                    "name": wheel_name,
                    "digest": {"sha256": digest}
                }
            ],
            "predicate": {
                "builder": {
                    "id": "https://github.com/DataDog/integrations-core/.github/workflows/release.yml@refs/heads/main"
                },
                "buildType": "https://github.com/DataDog/integrations-core/build/wheel/v1",
                "invocation": {
                    "configSource": {
                        "uri": f"git+https://github.com/DataDog/integrations-core@{os.getenv('GITHUB_SHA', 'unknown')}",
                        "digest": {"sha1": os.getenv('GITHUB_SHA', 'unknown')},
                        "entryPoint": ".github/workflows/release.yml"
                    }
                },
                "metadata": {
                    "buildInvocationId": os.getenv('GITHUB_RUN_ID', 'unknown'),
                    "buildStartedOn": datetime.now(timezone.utc).isoformat(),
                    "buildFinishedOn": datetime.now(timezone.utc).isoformat(),
                    "completeness": {
                        "parameters": True,
                        "environment": False,
                        "materials": False
                    },
                    "reproducible": False
                },
                "materials": [
                    {
                        "uri": f"git+https://github.com/DataDog/integrations-core@{os.getenv('GITHUB_SHA', 'unknown')}",
                        "digest": {"sha1": os.getenv('GITHUB_SHA', 'unknown')}
                    }
                ]
            }
        }

        # Save attestation
        attestation_file_name = f"{package_name}-{version}-attestation.json"
        attestation_path = os.path.join(package_path, "dist", attestation_file_name)
        with open(attestation_path, 'w') as f:
            json.dump(attestation, f, indent=2)
        print(f"Created attestation: {attestation_file_name}")

        # Calculate attestation hash
        with open(attestation_path, 'rb') as f:
            attestation_bytes = f.read()
            attestation_digest = hashlib.sha256(attestation_bytes).hexdigest()

        attestation_size = os.path.getsize(attestation_path)
        attestation_uri = ATTESTATION_URI_TEMPLATE.format(package_name, attestation_file_name)

        # Create pointer with attestation
        pointer = {
            "pointer": {
                "name": package_name,
                "version": version,
                "uri": uri,
                "digest": digest,
                "length": wheel_size,
                "attestation": {
                    "uri": attestation_uri,
                    "digest": attestation_digest,
                    "length": attestation_size
                }
            }
        }
        with open(
            os.path.join(package_path, "dist", f"{package_name}-{version}.pointer"), "w"
        ) as pointer_file:
            yaml.safe_dump(pointer, pointer_file)
            print("Created ", pointer_file.name, " with attestation metadata")

    return result


def upload_package(package_path, version, public=False):
    """Upload package wheel and/or pointer file to the S3 bucket.

    Args:
        package_path: Path to the package directory
        version: Package version string
        public: If True, upload both wheel and pointer (for public packages)

    Note: This requires AWS credentials to be available.
    Use aws-vault to run: aws-vault exec profile -- ddev release upload <check>
    """
    import glob
    import hashlib
    import os

    from botocore.exceptions import ClientError

    from datadog_checks.dev.tooling.aws_helpers import get_s3_client

    S3_BUCKET = "test-public-integration-wheels"
    S3_REGION = "eu-north-1"

    # Initialize S3 client
    s3 = get_s3_client(region=S3_REGION)

    folder_name = os.path.basename(package_path)
    package_name = get_package_name(folder_name)
    dist_dir = os.path.join(package_path, "dist")
    pointer_file_name = f"{package_name}-{version}.pointer"
    pointer_file_path = os.path.join(dist_dir, pointer_file_name)

    # Find the actual wheel file (e.g., package_name-version-py3-none-any.whl)
    wheel_pattern = os.path.join(
        dist_dir, f"{package_name.replace('-', '_')}-{version}-*.whl"
    )
    wheel_files = glob.glob(wheel_pattern)

    if not wheel_files:
        raise FileNotFoundError(
            f"No wheel file found matching pattern: {wheel_pattern}"
        )

    # Use the most recent wheel if multiple exist
    wheel_file_path = max(wheel_files, key=os.path.getctime)
    wheel_file_name = os.path.basename(wheel_file_path)

    # Calculate wheel hash
    with open(wheel_file_path, "rb") as f:
        wheel_hash = hashlib.sha256(f.read()).hexdigest()

    if public:
        # Upload both the pointer and the wheel to organized paths
        if not os.path.exists(pointer_file_path):
            raise FileNotFoundError(f"Pointer file not found: {pointer_file_path}")

        # Check for idempotency: if pointer already exists with same hash, skip
        pointer_s3_key = f"pointers/{package_name}/{pointer_file_name}"
        try:
            existing_pointer = s3.head_object(Bucket=S3_BUCKET, Key=pointer_s3_key)
            existing_digest = existing_pointer.get("Metadata", {}).get("digest", "")
            if existing_digest == wheel_hash:
                print(f"Version {version} already uploaded with same hash, skipping")
                return
            print(f"Warning: Version {version} exists with different hash, overwriting")
        except ClientError as e:
            if e.response["Error"]["Code"] != "404":
                raise
            # Doesn't exist, proceed with upload

        # Upload pointer file with metadata (public access via bucket policy)
        s3.upload_file(
            pointer_file_path,
            S3_BUCKET,
            pointer_s3_key,
            ExtraArgs={
                "Metadata": {"digest": wheel_hash, "version": version},
            },
        )

        # Upload wheel file with hash metadata (private, requires authentication)
        wheel_s3_key = f"simple/{package_name}/{wheel_file_name}"
        s3.upload_file(
            wheel_file_path,
            S3_BUCKET,
            wheel_s3_key,
            ExtraArgs={"Metadata": {"sha256": wheel_hash}},
        )

        print(
            f"Uploaded {pointer_file_name} and {wheel_file_name} to S3 bucket {S3_BUCKET}"
        )

        # Upload attestation file
        attestation_file_name = f"{package_name}-{version}-attestation.json"
        attestation_file_path = os.path.join(dist_dir, attestation_file_name)

        if os.path.exists(attestation_file_path):
            attestation_s3_key = f"attestations/{package_name}/{attestation_file_name}"
            s3.upload_file(
                attestation_file_path,
                S3_BUCKET,
                attestation_s3_key,
                ExtraArgs={"ContentType": "application/json"}
            )
            print(f"Uploaded attestation: {attestation_file_name}")
        else:
            print(f"Warning: No attestation file found at {attestation_file_path}")

        # Generate indexes
        from datadog_checks.dev.tooling.simple_index import (
            generate_package_index,
            generate_root_index,
        )

        print(f"Generating simple indexes...")
        generate_package_index(s3, S3_BUCKET, package_name, use_pointers=True)
        generate_root_index(s3, S3_BUCKET)
        print(f"Updated simple indexes for {package_name}")

    else:
        # Upload only the wheel to organized path
        wheel_s3_key = f"simple/{package_name}/{wheel_file_name}"
        s3.upload_file(
            wheel_file_path,
            S3_BUCKET,
            wheel_s3_key,
            ExtraArgs={"Metadata": {"sha256": wheel_hash}},
        )
        print(f"Uploaded {wheel_file_name} to S3 bucket {S3_BUCKET}")

        # Generate package index
        from datadog_checks.dev.tooling.simple_index import generate_package_index

        print(f"Generating simple index for {package_name}...")
        generate_package_index(s3, S3_BUCKET, package_name, use_pointers=False)
