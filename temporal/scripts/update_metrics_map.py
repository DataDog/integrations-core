# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from __future__ import annotations

import argparse
import pathlib
import sys

# We need access to METRIC_MAP and to helper functions from generate_metadata.py
# ``scripts`` is **not** a package, so add its parent (repository root) to sys.path
# so that ``import generate_metadata`` works both when the integration is installed
# and when running from source.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from scripts.generate_metadata import extract_metric_defs, fetch_temporal_metrics  # type: ignore
except ImportError as exc:  # pragma: no cover – should never happen inside repo
    raise SystemExit(f"Could not import helpers from generate_metadata.py: {exc}")

# Import the existing metrics map
# E402 Module level import not at top of file
# flake8: noqa: E402
from datadog_checks.temporal.metrics import METRIC_MAP

# Path to metrics.py that we will modify
METRICS_FILE = REPO_ROOT / "datadog_checks" / "temporal" / "metrics.py"


def build_version_var(tag: str) -> str:
    """Return the variable name for a given Temporal version tag.

    Example: ``v1.29.0`` -> ``TEMPORAL_V1_29_0_METRICS``.
    """
    cleaned = tag.lstrip("vV")  # strip leading 'v'
    var_suffix = cleaned.replace(".", "_")
    return f"TEMPORAL_V{var_suffix}_METRICS"


def append_version_dict(tag: str, missing: list[str]) -> None:
    """Append a new *version-specific* metric mapping dictionary to metrics.py.

    The generated block has the following structure::

        TEMPORAL_VX_YY_ZZ_METRICS = {
            'metric_a': 'metric_a', # TODO: verify mapping
            ...
        }

        METRIC_MAP.update(TEMPORAL_VX_YY_ZZ_METRICS)
    """

    var_name = build_version_var(tag)

    # Skip if dictionary already exists – prevents accidental duplication
    with METRICS_FILE.open("r", encoding="utf-8") as fp:
        if var_name in fp.read():
            print(f"⚠️  {var_name} already exists in metrics.py – nothing to do.")
            return

    header = f"\n{var_name} = {{\n"
    body = [f"    '{m}': '{m}',  # TODO: verify mapping\n" for m in sorted(missing)]
    footer = f"}}\n\nMETRIC_MAP.update({var_name})\n"

    block = header + "".join(body) + footer

    # Append to the end of the file. All existing version dicts are currently
    # declared at the end, so this keeps chronological order.
    with METRICS_FILE.open("a", encoding="utf-8") as fp:
        fp.write(block)

    print(f"Appended {len(missing)} new entries to {var_name} and updated METRIC_MAP.")


def main() -> None:
    """
    Compares Temporal's metric definitions for a specific release tag
    with our local ``METRIC_MAP`` and appends placeholder mappings for any **missing**
    metrics.

    1. Download ``common/metrics/metric_defs.go`` for the requested tag from the
    Temporal OSS repository.
    2. Extract all metric identifiers defined in that file.
    3. Compute the set difference between those identifiers and the keys already
    present in ``METRIC_MAP``.
    4. Append entries for the missing metrics to ``datadog_checks/temporal/metrics.py``
    as a new dictionary.
    5. Update the ``METRIC_MAP`` variable to include the new dictionary.

    For every newly-added metric we default the Datadog metric name to be identical to
    Temporal's.
    """
    parser = argparse.ArgumentParser(
        description="Update metrics.py with missing Temporal metrics.",
        epilog="Example: hatch run py3.8-1.19:python ./scripts/update_metrics_map.py --tag=v1.19.0",
    )
    parser.add_argument("--tag", required=True, help="Temporal version tag to compare against, e.g. v1.19.0")
    args = parser.parse_args()

    global ARGS_TAG  # expose to append_missing_metrics
    ARGS_TAG = args.tag

    # fetch & extract metrics from Temporal source
    source_go = fetch_temporal_metrics(args.tag)
    temporal_metric_types = extract_metric_defs(source_go)
    temporal_metrics = set(temporal_metric_types)

    # compute missing
    missing_metrics = sorted(temporal_metrics - set(METRIC_MAP))

    if not missing_metrics:
        print("✅ No missing metrics – METRIC_MAP is up to date!")
        return

    # update metrics.py by adding a new version-specific dictionary
    append_version_dict(args.tag, missing_metrics)

    print("💡 Please review the TODO comments and adjust metric names/types where necessary.")


if __name__ == "__main__":
    main()
