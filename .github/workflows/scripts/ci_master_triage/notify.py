#!/usr/bin/env python3
"""Format and post a Slack alert from ``triage_output.json``.

Real-time alerts (HIGH severity) lead with the breakage; digests summarize all
new failed runs since the last digest. Optional root-cause enrichment is read
from ``ENRICHMENT_FILE`` when present. Set ``DRY_RUN=1`` to print the payload
without posting (used by the verification step).
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

from common import FailedTarget, RunRecord, TriageOutput, env

POST_URL = "https://slack.com/api/chat.postMessage"
MAX_RUNS_SHOWN = 15
MAX_TARGETS_PER_RUN = 20
REQUEST_TIMEOUT = 30


def target_line(targets: list[FailedTarget]) -> str:
    """Render failed targets as linked job-names, capped for readability."""
    shown = targets[:MAX_TARGETS_PER_RUN]
    links = []
    for t in shown:
        link = f"<{t['url']}|{t['job_name']}>"
        if t.get("leg_count", 1) > 1:
            link += f" _×{t['leg_count']}_"
        links.append(link)
    extra = len(targets) - len(shown)
    if extra > 0:
        links.append(f"_+{extra} more_")
    return ", ".join(links)


def run_block(run: RunRecord, enrichment: dict[str, str]) -> dict[str, Any]:
    """One Slack section block summarizing a single broken run."""
    header = (
        f"*<{run['url']}|{run['workflow']}>* · `{run['short_sha']}` · "
        f"{run['failed_count']} target(s) failing · _{run['actor']}_"
    )
    lines = [header, f">{run['title']}", target_line(run["failed_targets"])]
    note = enrichment.get(str(run["run_id"]))
    if note:
        lines.append(f":mag: {note}")
    return {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}


def build_blocks(data: TriageOutput, enrichment: dict[str, str]) -> list[dict[str, Any]]:
    runs = data["runs"]
    realtime = data["mode"] == "realtime"
    if realtime:
        title = f":rotating_light: Master CI broken ({data['severity']}) — {len(runs)} run(s)"
    else:
        title = f":bar_chart: Master CI digest — {len(runs)} new broken run(s)"

    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": title[:150], "emoji": True}}
    ]
    for run in runs[:MAX_RUNS_SHOWN]:
        blocks.append(run_block(run, enrichment))

    if len(runs) > MAX_RUNS_SHOWN:
        blocks.append(
            {"type": "context", "elements": [{"type": "mrkdwn", "text": f"_…and {len(runs) - MAX_RUNS_SHOWN} more run(s)._"}]}
        )

    footer = [f"<{data['dashboard_url']}|CI Overview dashboard>"]
    if data.get("non_test_failure_count"):
        footer.append(f"{data['non_test_failure_count']} failed run(s) had no failing tests (infra / re-run).")
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": " · ".join(footer)}]})
    return blocks


def fallback_text(data: TriageOutput) -> str:
    return f"Master CI {data['mode']} — {len(data['runs'])} broken run(s) ({data['severity']})"


def post(channel: str, token: str, blocks: list[dict[str, Any]], text: str) -> None:
    body = json.dumps({"channel": channel, "blocks": blocks, "text": text}).encode()
    req = urllib.request.Request(
        POST_URL,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        result = json.loads(resp.read().decode())
    if not result.get("ok"):
        raise RuntimeError(f"Slack API error: {result}")
    print(f"Posted to {channel} (ts={result.get('ts')})")


def main() -> int:
    data = json.loads(Path(env("TRIAGE_OUTPUT", "triage_output.json")).read_text())
    if not data.get("runs"):
        print("No runs to report; nothing posted.")
        return 0

    enrichment: dict[str, str] = {}
    enrichment_file = env("ENRICHMENT_FILE")
    if enrichment_file and Path(enrichment_file).exists():
        try:
            enrichment = json.loads(Path(enrichment_file).read_text())
        except json.JSONDecodeError:
            print("Enrichment file is not valid JSON; posting without it.", file=sys.stderr)

    blocks = build_blocks(data, enrichment)
    text = fallback_text(data)

    if env("DRY_RUN"):
        print(json.dumps({"text": text, "blocks": blocks}, indent=2))
        return 0

    token = env("SLACK_API_TOKEN")
    channel = env("SLACK_CHANNEL_ID", "C026U34QMLL")
    if not token:
        print("SLACK_API_TOKEN is required to post", file=sys.stderr)
        return 1
    try:
        post(channel, token, blocks, text)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
