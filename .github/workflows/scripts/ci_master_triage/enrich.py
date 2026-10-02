#!/usr/bin/env python3
"""Best-effort root-cause enrichment for the master CI triage alert.

Reads ``triage_output.json`` (produced by ``detect.py``), fetches the
failed-step logs for each enrichment job via ``gh``, asks Claude for a one-line
root cause per run, and writes ``{run_id: note}`` to ``ENRICHMENT_FILE``.

This step is optional and gated by ``detect.py``: it only runs when there is
something to alert on and ``ANTHROPIC_API_KEY`` is present. Any failure degrades
to an empty mapping so the Slack alert is still posted (with links only).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from common import TriageOutput, env

MODEL = "claude-opus-4-8"
MAX_TOKENS = 8000
MAX_LOG_LINES = 200


def fetch_failed_log(repo: str, gh_job_id: str) -> str:
    """Return the failed-step logs for a single job, trimmed to the tail."""
    if not gh_job_id:
        return "(no job id)"
    try:
        proc = subprocess.run(
            ["gh", "run", "view", "--repo", repo, "--job", gh_job_id, "--log-failed"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        return f"(log fetch failed: {exc})"
    if proc.returncode != 0:
        detail = proc.stderr.strip() or "no stderr"
        return f"(gh exit {proc.returncode}: {detail})"
    output = proc.stdout or "(no output)"
    lines = output.splitlines()
    return "\n".join(lines[-MAX_LOG_LINES:])


def build_logs_section(repo: str, jobs: list[dict[str, str]]) -> str:
    """Assemble the ``{{LOGS}}`` body: one delimited block per enrichment job."""
    blocks: list[str] = []
    for job in jobs:
        header = f"### RUN {job.get('run_id', '?')} · TARGET {job.get('target', '?')}"
        blocks.append(f"{header}\n{fetch_failed_log(repo, job.get('gh_job_id', ''))}")
    return "\n\n".join(blocks)


def render_prompt(prompt_file: Path, logs: str) -> str:
    template = prompt_file.read_text()
    return template.replace("{{LOGS}}", logs)


def call_claude(prompt: str) -> str:
    """Return Claude's text response, or empty string on a handled API error."""
    from anthropic import Anthropic, APIConnectionError, APIStatusError

    client = Anthropic()
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        )
    except APIStatusError as exc:
        print(f"Anthropic API error ({exc.status_code}); skipping enrichment.", file=sys.stderr)
        return ""
    except APIConnectionError as exc:
        print(f"Anthropic connection error ({exc}); skipping enrichment.", file=sys.stderr)
        return ""
    if resp.stop_reason == "refusal":
        print("Request refused; skipping enrichment.", file=sys.stderr)
        return ""
    return "".join(block.text for block in resp.content if block.type == "text")


def parse_enrichment(text: str) -> dict[str, str]:
    """Pull a ``{run_id: note}`` object out of the model response."""
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*?\}", text, re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(k): str(v) for k, v in parsed.items()}


def main() -> int:
    out_path = Path(env("ENRICHMENT_FILE", "enrichment.json"))
    out_path.write_text("{}")  # ensure the file exists even if we bail early

    data: TriageOutput = json.loads(Path(env("TRIAGE_OUTPUT", "triage_output.json")).read_text())
    jobs: list[dict[str, str]] = data.get("enrichment_jobs", [])
    if not jobs:
        print("No enrichment jobs; wrote empty mapping.")
        return 0

    repo = env("GITHUB_REPOSITORY", "DataDog/integrations-core")
    prompt_file = Path(env("PROMPT_FILE", str(Path(__file__).parent / "enrich_prompt.md")))

    logs = build_logs_section(repo, jobs)
    text = call_claude(render_prompt(prompt_file, logs))
    enrichment = parse_enrichment(text)

    out_path.write_text(json.dumps(enrichment, indent=2))
    print(f"Wrote {len(enrichment)} enrichment note(s) to {out_path}.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - enrichment must never block the alert
        print(f"Enrichment failed ({exc}); continuing without it.", file=sys.stderr)
        Path(env("ENRICHMENT_FILE", "enrichment.json")).write_text("{}")
        sys.exit(0)
