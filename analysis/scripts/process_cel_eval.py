#!/usr/bin/env -S uv run --quiet --no-project --with cel-python --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["cel-python"]
# ///
"""Evaluate per-integration CEL rules against collected process data.

For each integration with a CEL rule (from analysis/process_autodiscovery/cel_rules.json
or, when absent there, derived from manifest.json process_signatures), this:

1. Loads the collected process tree (data/<integration>__<env>.json).
2. Applies `isMainProcessForService` to find the candidate set.
3. Evaluates the CEL rule against each candidate using cel-python.
4. Reports how many processes survive both filters.

The CEL evaluation uses the same field shape the agent presents to integration
rules: `process.name` (workloadmeta.Process.Name, which the agent populates from
/proc/<pid>/status Name — subject to the 15-character kernel comm limit),
`process.cmdline` (joined cmdline), and `process.args` (cmdline split on spaces).
See comp/core/workloadfilter/util/workloadmeta/create.go in datadog-agent.

This script is run via `uv run` so cel-python is fetched on demand and does
not need to be a project dependency.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import celpy

REPO_ROOT = Path(__file__).parent.parent.parent
DEFAULT_DATA_DIR = REPO_ROOT / "analysis" / "process_autodiscovery" / "data"
DEFAULT_RULES_FILE = REPO_ROOT / "analysis" / "process_autodiscovery" / "cel_rules.json"

INFRA = {"agent", "system-probe", "security-agent", "privateactionrunner"}


@dataclass
class Rule:
    integration: str
    expression: str
    source: str
    notes: str = ""


@dataclass
class Survivor:
    pid: int
    name: str
    generated_name: str | None
    cmdline: str


def is_main_process(p: dict, by_pid: dict[int, dict]) -> bool:
    """Python equivalent of isMainProcessForService."""
    if p["ppid"] in (0, 1):
        return True
    parent = by_pid.get(p["ppid"])
    if parent is None or not parent["has_service_data"]:
        return True
    return parent["generated_name"] != p["generated_name"]


def load_manifest_signatures(integration: str) -> list[str] | None:
    """Find process_signatures in the integration's manifest.json, if any.

    The path is conventionally manifest.assets.integration.process_signatures,
    but some manifests nest it differently; walk the tree.
    """
    path = REPO_ROOT / integration / "manifest.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            m = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    def walk(obj):
        if isinstance(obj, dict):
            if "process_signatures" in obj and isinstance(obj["process_signatures"], list):
                return obj["process_signatures"]
            for v in obj.values():
                r = walk(v)
                if r is not None:
                    return r
        return None

    return walk(m)


def cel_from_signatures(signatures: list[str]) -> str:
    """OR-join process_signatures into a cmdline.contains(...) CEL expression."""
    escaped = [s.replace("\\", "\\\\").replace("'", "\\'") for s in signatures]
    return " || ".join(f"process.cmdline.contains('{s}')" for s in escaped)


def build_rules(rules_file: Path, integrations: list[str]) -> dict[str, Rule]:
    """Build the rule set: explicit overrides + manifest fallback."""
    with open(rules_file) as f:
        explicit = json.load(f)
    rules: dict[str, Rule] = {}
    for integration in integrations:
        if integration in explicit:
            entry = explicit[integration]
            rules[integration] = Rule(
                integration=integration,
                expression=entry["expression"],
                source=entry.get("source", "manual"),
                notes=entry.get("notes", ""),
            )
            continue
        sigs = load_manifest_signatures(integration)
        if sigs:
            rules[integration] = Rule(
                integration=integration,
                expression=cel_from_signatures(sigs),
                source="manifest",
                notes=f"derived from manifest.json process_signatures: {sigs}",
            )
    return rules


def integrations_with_target_service(data_dir: Path) -> list[str]:
    """Return integrations whose collected data contains at least one non-infra service."""
    result = []
    for path in sorted(data_dir.glob("*__*.json")):
        if path.name == "skipped.json":
            continue
        try:
            with open(path) as f:
                d = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        for p in d["processes"]:
            if p.get("has_service_data") and p.get("generated_name") not in INFRA:
                result.append(path.stem.split("__")[0])
                break
    return sorted(set(result))


def evaluate(data_path: Path, rule: Rule) -> tuple[list[Survivor], list[Survivor], str | None]:
    """Return (mains, survivors, error).

    mains: non-infra processes selected by is_main_process.
    survivors: subset of mains for which the CEL rule evaluates true.
    error: compile or evaluation error, if any.
    """
    with open(data_path) as f:
        d = json.load(f)
    by_pid = {p["pid"]: p for p in d["processes"]}

    mains: list[Survivor] = []
    for p in d["processes"]:
        if not p["has_service_data"]:
            continue
        if p["generated_name"] in INFRA:
            continue
        if not is_main_process(p, by_pid):
            continue
        mains.append(
            Survivor(
                pid=p["pid"],
                name=p["comm"],
                generated_name=p.get("generated_name"),
                cmdline=p["cmdline"],
            )
        )

    env = celpy.Environment()
    try:
        ast = env.compile(rule.expression)
        program = env.program(ast)
    except Exception as e:  # noqa: BLE001 — celpy raises bare Exception subclasses
        return mains, [], f"compile error: {e}"

    survivors: list[Survivor] = []
    for m in mains:
        process_input = celpy.json_to_cel(
            {
                "name": m.name,
                "cmdline": m.cmdline,
                "args": m.cmdline.split(),
            }
        )
        try:
            result = program.evaluate({"process": process_input})
        except Exception as e:  # noqa: BLE001
            return mains, [], f"eval error on pid {m.pid}: {e}"
        if bool(result):
            survivors.append(m)
    return mains, survivors, None


def format_report(rows: list[dict], detail: bool) -> str:
    lines: list[str] = []
    col = (24, 8, 8, 10, 60)
    header = (
        f"{'Integration':<{col[0]}}"
        f"{'Mains':<{col[1]}}"
        f"{'PostCEL':<{col[2]}}"
        f"{'Source':<{col[3]}}"
        f"{'Expression':<{col[4]}}"
    )
    lines.append(header)
    lines.append("-" * sum(col))
    for r in rows:
        expr = r["expression"]
        if len(expr) > col[4] - 1:
            expr = expr[: col[4] - 4] + "..."
        lines.append(
            f"{r['integration']:<{col[0]}}"
            f"{r['mains']:<{col[1]}}"
            f"{r['post_cel']:<{col[2]}}"
            f"{r['source']:<{col[3]}}"
            f"{expr:<{col[4]}}"
        )
        if r.get("error"):
            lines.append(f"  ERROR: {r['error']}")
        if detail:
            for s in r["survivor_detail"]:
                lines.append(
                    f"    survivor pid={s['pid']} name={s['name']!r} gn={s['generated_name']!r}"
                )
                lines.append(f"      cmdline={s['cmdline'][:140]}")
            if r.get("dropped_detail"):
                for s in r["dropped_detail"]:
                    lines.append(
                        f"    dropped  pid={s['pid']} name={s['name']!r} gn={s['generated_name']!r}"
                    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rules", type=Path, default=DEFAULT_RULES_FILE, help="Explicit CEL rules JSON"
    )
    parser.add_argument(
        "--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Collected data directory"
    )
    parser.add_argument(
        "--integration", help="Limit to a single integration (otherwise all with target data)"
    )
    parser.add_argument(
        "--detail",
        action="store_true",
        help="Print per-process detail rows for each integration",
    )
    parser.add_argument(
        "--json-output", type=Path, help="Also write machine-readable JSON to this path"
    )
    args = parser.parse_args()

    if args.integration:
        targets = [args.integration]
    else:
        targets = integrations_with_target_service(args.data_dir)

    rules = build_rules(args.rules, targets)
    rows: list[dict] = []
    for integration in targets:
        if integration not in rules:
            rows.append(
                {
                    "integration": integration,
                    "expression": "(no rule)",
                    "source": "missing",
                    "mains": 0,
                    "post_cel": 0,
                    "error": None,
                    "survivor_detail": [],
                    "dropped_detail": [],
                }
            )
            continue
        rule = rules[integration]
        candidates = list(args.data_dir.glob(f"{integration}__*.json"))
        if not candidates:
            continue
        mains, survivors, error = evaluate(candidates[0], rule)
        survivor_pids = {s.pid for s in survivors}
        rows.append(
            {
                "integration": integration,
                "expression": rule.expression,
                "source": rule.source,
                "notes": rule.notes,
                "mains": len(mains),
                "post_cel": len(survivors),
                "error": error,
                "survivor_detail": [
                    {"pid": s.pid, "name": s.name, "generated_name": s.generated_name, "cmdline": s.cmdline}
                    for s in survivors
                ],
                "dropped_detail": [
                    {"pid": m.pid, "name": m.name, "generated_name": m.generated_name, "cmdline": m.cmdline}
                    for m in mains
                    if m.pid not in survivor_pids
                ],
            }
        )

    print(format_report(rows, args.detail))

    if args.json_output:
        with open(args.json_output, "w") as f:
            json.dump({"results": rows}, f, indent=2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
