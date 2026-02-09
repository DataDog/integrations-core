"""Command-line interface for the release package."""

import hashlib
import json
import sys
from pathlib import Path

import click

from release.core import IntegrationBuilder, TargetGenerator


@click.group()
def cli():
    """Build and release Agent integration wheels."""
    pass


@cli.command()
@click.argument("integration")
@click.option(
    "--source-dir",
    default=".",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Source directory containing the integration",
)
def build(integration, source_dir):
    """Build an integration wheel.

    \b
    Examples:
        release build postgres
        release build postgres --source-dir /path/to/integrations-core

    \b
    Output:
        JSON object with build metadata (integration, version, wheel_path, etc.)
    """
    builder = IntegrationBuilder(source_dir)

    try:
        result = builder.build(integration)

        output = {
            "integration": result.integration,
            "version": result.version,
            "wheel_path": str(result.wheel_path),
            "wheel_digest": result.wheel_digest,
            "wheel_size": result.wheel_size,
            "wheel_filename": result.wheel_path.name,
        }

        click.echo(json.dumps(output, indent=2))

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("integrations_json")
@click.option(
    "--max-count",
    type=int,
    default=256,
    help="Maximum number of integrations allowed",
)
def validate_integrations(integrations_json, max_count):
    """Validate and parse a JSON array of integration names.

    \b
    Examples:
        release validate-integrations '["postgres", "mysql", "redis"]'
        release validate-integrations '["postgres"]' --max-count 100

    \b
    Output:
        JSON object with validation results and parsed list
    """
    try:
        # Parse JSON
        try:
            integrations = json.loads(integrations_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

        # Validate it's a list
        if not isinstance(integrations, list):
            raise ValueError(f"Expected JSON array, got {type(integrations).__name__}")

        # Validate it's not empty
        if len(integrations) == 0:
            raise ValueError("Integration list cannot be empty")

        # Validate count
        if len(integrations) > max_count:
            raise ValueError(
                f"Too many integrations: {len(integrations)} > {max_count}"
            )

        # Validate all items are strings
        for i, item in enumerate(integrations):
            if not isinstance(item, str):
                raise ValueError(
                    f"Integration at index {i} is not a string: {type(item).__name__}"
                )
            if not item.strip():
                raise ValueError(f"Integration at index {i} is empty or whitespace")

        # Output result
        output = {
            "valid": True,
            "count": len(integrations),
            "integrations": integrations,
        }
        click.echo(json.dumps(output, indent=2))

    except Exception as e:
        output = {
            "valid": False,
            "error": str(e),
        }
        click.echo(json.dumps(output, indent=2))
        sys.exit(1)


@cli.command()
@click.option("--integration", required=True, help="Integration name")
@click.option("--version", required=True, help="Integration version")
@click.option("--wheel-digest", required=True, help="SHA256 digest of the wheel")
@click.option(
    "--wheel-size", required=True, type=int, help="Size of the wheel in bytes"
)
@click.option("--wheel-filename", required=True, help="Name of the wheel file")
@click.option("--attestation-digest", help="SHA256 digest of the attestation")
@click.option(
    "--attestation-path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to attestation file (will calculate digest)",
)
@click.option("--repository-url", required=True, help="Base URL of the S3 repository")
@click.option(
    "--output-dir",
    default="targets",
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory for target files",
)
def target(
    integration,
    version,
    wheel_digest,
    wheel_size,
    wheel_filename,
    attestation_digest,
    attestation_path,
    repository_url,
    output_dir,
):
    """Generate a TUF target file (wheel manifest).

    \b
    Examples:
        release target --integration postgres --version 23.2.0 \\
                       --wheel-digest abc123... --wheel-size 100905 \\
                       --wheel-filename datadog_postgres-23.2.0-py3-none-any.whl \\
                       --attestation-path /path/to/attestation.jsonl \\
                       --repository-url https://my-bucket.s3.amazonaws.com
    """
    generator = TargetGenerator(repository_url)

    try:
        # Calculate attestation digest if not provided but path is
        if not attestation_digest and attestation_path:
            with open(attestation_path, "rb") as f:
                attestation_digest = hashlib.sha256(f.read()).hexdigest()

        if not attestation_digest:
            raise click.ClickException(
                "Either --attestation-digest or --attestation-path must be provided"
            )

        # Generate and write target
        target_data = generator.generate_target(
            integration=integration,
            version=version,
            wheel_digest=wheel_digest,
            wheel_size=wheel_size,
            wheel_filename=wheel_filename,
            attestation_digest=attestation_digest,
        )

        target_file = generator.write_target(target_data, output_dir)

        click.echo(f"Generated target file: {target_file}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--input-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Input directory containing downloaded target artifacts",
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory for organized target files",
)
def organize_targets(input_dir, output_dir):
    """Organize target artifact files into a flat structure.

    GitHub Actions downloads artifacts into subdirectories. This command
    flattens the structure and organizes targets by integration name.

    \b
    Examples:
        release organize-targets --input-dir targets-raw/ --output-dir targets-organized/

    \b
    Output:
        JSON object with organization results
    """
    try:
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find all YAML target files
        target_files = list(input_dir.rglob("*.yaml"))

        if not target_files:
            raise ValueError(f"No target files (*.yaml) found in {input_dir}")

        organized = []

        for file_path in target_files:
            # Get the integration directory name
            # Artifacts are downloaded as: targets-raw/target-{integration}-{version}/{integration}/{version}.yaml
            # We need to extract the integration name from the directory structure

            # The parent directory of the YAML file should be the integration name
            integration_name = file_path.parent.name

            # Create target directory
            target_dir = output_dir / integration_name
            target_dir.mkdir(parents=True, exist_ok=True)

            # Copy the file
            dest_path = target_dir / file_path.name

            # Read and write to ensure proper copying
            dest_path.write_bytes(file_path.read_bytes())

            organized.append(
                {
                    "source": str(file_path),
                    "destination": str(dest_path),
                    "integration": integration_name,
                }
            )

        # Output results
        output = {
            "success": True,
            "files_organized": len(organized),
            "details": organized,
        }
        click.echo(json.dumps(output, indent=2))

    except Exception as e:
        output = {
            "success": False,
            "error": str(e),
        }
        click.echo(json.dumps(output, indent=2), err=True)
        sys.exit(1)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
