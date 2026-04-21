#!/usr/bin/env python
"""Run a multi-phase AI pipeline that scaffolds a uv-managed Python package.

Usage (from the integrations-core repo root, using the ddev venv):

    python demo/demo.py path/to/spec.md

Or with a custom output directory:

    python demo/demo.py path/to/spec.md --output /tmp/my_output

ANTHROPIC_API_KEY must be set in the environment.

Pipeline:
    plan → setup_package → [write_tool | write_usage] → write_tests
"""

import os
import tempfile
from pathlib import Path

import anthropic
import click


@click.command(help="AI pipeline that builds a uv-managed Python package from SPEC.")
@click.argument(
    "spec",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True, path_type=Path),
)
@click.option(
    "--output",
    "output",
    default=None,
    type=click.Path(file_okay=False, resolve_path=True, path_type=Path),
    help="Output directory (default: fresh temp dir).",
)
def main(spec: Path, output: Path | None) -> None:
    flow_dir = Path(__file__).parent / "flow"
    output_dir = output if output is not None else Path(tempfile.mkdtemp(prefix="uv_demo_"))
    output_dir.mkdir(parents=True, exist_ok=True)

    click.echo("=" * 64)
    click.echo("  uv Package AI Demo")
    click.echo("  Pipeline:  plan → setup_package → [write_tool | write_usage] → write_tests")
    click.echo(f"  Spec:      {spec}")
    click.echo(f"  Output:    {output_dir}")
    click.echo("=" * 64)
    click.echo()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise click.UsageError("ANTHROPIC_API_KEY is not set in the environment.")

    from ddev.ai.phases.orchestrator import PhaseOrchestrator
    from ddev.ai.react.rich_printer import make_rich_callbacks
    from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy

    client = anthropic.AsyncAnthropic()
    rich_callbacks = make_rich_callbacks()

    orchestrator = PhaseOrchestrator(
        flow_yaml_path=flow_dir / "flow.yaml",
        checkpoint_path=output_dir / "checkpoints.yaml",
        runtime_variables={
            "output_dir": str(output_dir),
            "spec_path": str(spec),
        },
        anthropic_client=client,
        callback_sets=[rich_callbacks],
        grace_period=5,
        max_timeout=2 * 60 * 60,  # 2 hours
        file_access_policy=FileAccessPolicy(write_root=output_dir),
    )

    try:
        orchestrator.run()
    except Exception as e:
        click.echo(f"\nPipeline failed: {e}", err=True)
        raise

    click.echo()
    click.echo("=" * 64)
    click.echo("  Done!")
    click.echo()
    click.echo("  Output files:")
    for p in sorted(output_dir.rglob("*")):
        if p.is_file():
            click.echo(f"    {p.relative_to(output_dir)}")
    click.echo("=" * 64)


if __name__ == "__main__":
    main()
