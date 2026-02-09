"""Integration wheel building and TUF target generation.

This module provides functionality for:
- Building integration wheels and detecting versions
- Generating TUF target files (wheel manifests) for secure distribution

TUF targets are wheel manifest files that contain metadata about integration wheels,
including their location, digest, and attestation. These manifests are secured by TUF
to ensure integrity and authenticity of the wheels during distribution.
"""

import ast
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class BuildResult:
    """Result of building an integration wheel."""

    integration: str
    version: str
    wheel_path: Path
    wheel_digest: str
    wheel_size: int


@dataclass
class TargetData:
    """Data for a TUF target file (wheel manifest)."""

    integration: str
    version: str
    digest: str
    length: int
    repository: str
    wheel_path: str
    attestation_path: str

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "digest": self.digest,
            "length": self.length,
            "version": self.version,
            "repository": self.repository,
            "wheel_path": self.wheel_path,
            "attestation_path": self.attestation_path,
        }


class IntegrationBuilder:
    """Builds integration wheels and detects versions."""

    def __init__(self, source_dir: Path):
        """
        Initialize the builder.

        Args:
            source_dir: Root directory of the integration source repository
        """
        self.source_dir = Path(source_dir)

    def detect_version(self, integration_name: str) -> str:
        """
        Detect the version of an integration from its __about__.py file.

        Args:
            integration_name: Name of the integration

        Returns:
            Version string

        Raises:
            FileNotFoundError: If __about__.py cannot be found
            ValueError: If version cannot be extracted
        """
        about_file = (
            self.source_dir
            / integration_name
            / "datadog_checks"
            / integration_name
            / "__about__.py"
        )

        if not about_file.exists():
            # Try to provide helpful error message
            datadog_checks_dir = (
                self.source_dir / integration_name / "datadog_checks"
            )
            if datadog_checks_dir.exists():
                available = [d.name for d in datadog_checks_dir.iterdir() if d.is_dir()]
                raise FileNotFoundError(
                    f"Cannot find {about_file}\n"
                    f"Available packages in datadog_checks/: {available}"
                )
            raise FileNotFoundError(f"Cannot find {about_file}")

        # Safely parse the file using AST to extract __version__
        with open(about_file) as f:
            tree = ast.parse(f.read(), filename=str(about_file))

        version = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__version__":
                        # Extract the value - should be a string literal
                        if isinstance(node.value, ast.Constant):
                            version = node.value.value
                        elif isinstance(
                            node.value, ast.Str
                        ):  # Python 3.7 compatibility
                            version = node.value.s
                        break
            if version:
                break

        if not version:
            raise ValueError(f"Could not find __version__ in {about_file}")

        if not isinstance(version, str):
            raise ValueError(
                f"__version__ must be a string literal in {about_file}, got {type(version).__name__}"
            )

        return version

    def build_wheel(self, integration_name: str) -> Path:
        """
        Build a wheel for the specified integration.

        Args:
            integration_name: Name of the integration to build

        Returns:
            Path to the built wheel file

        Raises:
            subprocess.CalledProcessError: If build fails
            FileNotFoundError: If wheel file not found after build
            ValueError: If multiple wheels found
        """
        integration_dir = self.source_dir / integration_name

        if not integration_dir.exists():
            raise FileNotFoundError(
                f"Integration directory not found: {integration_dir}"
            )

        # Build the wheel
        subprocess.run(
            ["python", "-m", "build", "--wheel", str(integration_dir)],
            capture_output=True,
            text=True,
            check=True,
        )

        # Find the built wheel
        dist_dir = integration_dir / "dist"
        wheels = list(dist_dir.glob("*.whl"))

        if len(wheels) == 0:
            raise FileNotFoundError(f"No wheel file found in {dist_dir} after build")
        elif len(wheels) > 1:
            raise ValueError(f"Multiple wheel files found in {dist_dir}: {wheels}")

        return wheels[0]

    def calculate_digest(self, file_path: Path) -> str:
        """
        Calculate SHA256 digest of a file.

        Args:
            file_path: Path to the file

        Returns:
            Hex digest string
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def build(self, integration_name: str) -> BuildResult:
        """
        Build an integration wheel and collect all metadata.

        This is the main entry point that combines version detection,
        wheel building, and metadata collection.

        Args:
            integration_name: Name of the integration to build

        Returns:
            BuildResult with all build metadata

        Example:
            >>> builder = IntegrationBuilder(Path("/path/to/integrations-core"))
            >>> result = builder.build("postgres")
            >>> print(result.version)
            '23.2.0'
        """
        # Detect version first
        version = self.detect_version(integration_name)

        # Build wheel
        wheel_path = self.build_wheel(integration_name)

        # Calculate digest and size
        digest = self.calculate_digest(wheel_path)
        size = wheel_path.stat().st_size

        return BuildResult(
            integration=integration_name,
            version=version,
            wheel_path=wheel_path,
            wheel_digest=digest,
            wheel_size=size,
        )


class TargetGenerator:
    """Generates TUF target files (wheel manifests) for integration wheels."""

    def __init__(self, repository_url: str):
        """
        Initialize the target generator.

        Args:
            repository_url: Base URL of the S3 repository (e.g., https://bucket.s3.amazonaws.com)
        """
        self.repository_url = repository_url.rstrip("/")

    def generate_target(
        self,
        integration: str,
        version: str,
        wheel_digest: str,
        wheel_size: int,
        wheel_filename: str,
        attestation_digest: str,
    ) -> TargetData:
        """
        Generate TUF target metadata (wheel manifest) for a specific version.

        The target file contains metadata that allows clients to verify the integrity
        and authenticity of the wheel before downloading it.

        Args:
            integration: Integration name
            version: Version string
            wheel_digest: SHA256 digest of the wheel
            wheel_size: Size of the wheel in bytes
            wheel_filename: Name of the wheel file
            attestation_digest: SHA256 digest of the attestation

        Returns:
            TargetData object

        Example:
            >>> gen = TargetGenerator("https://my-bucket.s3.amazonaws.com")
            >>> target = gen.generate_target(
            ...     "postgres", "23.2.0", "abc123...", 100905,
            ...     "datadog_postgres-23.2.0-py3-none-any.whl",
            ...     "def456..."
            ... )
        """
        wheel_path = f"/wheels/datadog-{integration}/{wheel_filename}"
        attestation_path = f"/attestations/{attestation_digest}.json"

        return TargetData(
            integration=integration,
            version=version,
            digest=wheel_digest,
            length=wheel_size,
            repository=self.repository_url,
            wheel_path=wheel_path,
            attestation_path=attestation_path,
        )

    def write_target(self, target_data: TargetData, output_dir: Path) -> Path:
        """
        Write a TUF target file (wheel manifest) for a specific version.

        Creates: datadog-{integration}/{version}.yaml

        Args:
            target_data: Target data to write
            output_dir: Directory to write the target file

        Returns:
            Path to the written file

        Example:
            >>> gen = TargetGenerator("https://my-bucket.s3.amazonaws.com")
            >>> path = gen.write_target(target_data, Path("targets"))
            >>> # Creates: targets/datadog-postgres/23.2.0.yaml
        """
        integration_dir = output_dir / f"datadog-{target_data.integration}"
        integration_dir.mkdir(parents=True, exist_ok=True)

        target_file = integration_dir / f"{target_data.version}.yaml"

        with open(target_file, "w") as f:
            yaml.safe_dump(target_data.to_dict(), f, default_flow_style=False, sort_keys=False)

        return target_file
