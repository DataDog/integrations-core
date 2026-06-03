"""Check TUF root metadata: verify local file matches remote and warn when close to expiring."""

import difflib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


S3_BUCKET_ROOT = "https://dd-integrations-core-wheels-build-stable.datadoghq.com/metadata.staged/root.json"
DOWNLOADER_ROOT = Path("datadog_checks_downloader/datadog_checks/downloader/data/repo/metadata/root.json")

WARN_DAYS = [60, 30, 14]
DAILY_WARN_THRESHOLD = 10

REQUEST_TIMEOUT = 30
MAX_RETRIES = 10
BACKOFF_BASE = 5
BACKOFF_MAX = 600

GITHUB_SERVER_URL = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
GITHUB_RUN_ID = os.environ.get("GITHUB_RUN_ID", "")
CI_LOGS_URL = f"{GITHUB_SERVER_URL}/{GITHUB_REPOSITORY}/actions/runs/{GITHUB_RUN_ID}"

SLACK_API_TOKEN = os.environ["SLACK_API_TOKEN"]
SLACK_CHANNEL_IDS = os.environ["SLACK_CHANNEL_IDS"].split(",")
DEBUG_RUN = os.environ.get("DEBUG_RUN", "").lower() == "true"


def urlopen_with_retry(url: str | urllib.request.Request) -> bytes:
    for attempt in range(MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as resp:
                return resp.read()
        except urllib.error.URLError as e:
            if attempt == MAX_RETRIES:
                raise
            delay = min(BACKOFF_BASE * 2**attempt, BACKOFF_MAX)
            print(f"Request failed ({e}), retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})")
            time.sleep(delay)
    raise RuntimeError("unreachable")


def post_slack_message(text: str) -> None:
    for channel_id in SLACK_CHANNEL_IDS:
        payload = json.dumps({"channel": channel_id.strip(), "text": text}).encode()
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=payload,
            headers={
                "Authorization": f"Bearer {SLACK_API_TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            data = urlopen_with_retry(req)
            result = json.loads(data.decode())
            if not result.get("ok"):
                print(f"Slack error for channel {channel_id}: {result.get('error')}", file=sys.stderr)
        except urllib.error.URLError as e:
            print(f"Slack request failed for channel {channel_id}: {e}", file=sys.stderr)


def main() -> None:
    errors: list[str] = []

    remote_raw = urlopen_with_retry(S3_BUCKET_ROOT)
    remote = json.loads(remote_raw.decode())
    local = json.loads(DOWNLOADER_ROOT.read_text())

    if local != remote:
        local_lines = json.dumps(local, indent=2, sort_keys=True).splitlines(keepends=True)
        remote_lines = json.dumps(remote, indent=2, sort_keys=True).splitlines(keepends=True)
        diff = "".join(difflib.unified_diff(local_lines, remote_lines, fromfile="downloader/root.json", tofile="s3-bucket/root.json"))
        print(diff)
        errors.append(f":x: TUF root mismatch between `downloader/root.json` and `s3-bucket/root.json`. See diff in CI logs: {CI_LOGS_URL}")

    expires_str = local["signed"]["expires"]
    expires = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    days_remaining = (expires - now).days

    print(f"TUF root expires: {expires_str} ({days_remaining} days remaining)")

    if DEBUG_RUN:
        match_status = (
            ":white_check_mark: Local and remote `root.json` match."
            if not errors
            else ":x: Local and remote `root.json` do *not* match."
        )
        post_slack_message(
            f":ladybug: *Debug run*\n"
            f"{match_status}\n"
            f"Metadata expires on `{expires_str}` ({days_remaining} days remaining)."
        )

    if errors:
        post_slack_message("\n".join(errors))
        sys.exit(1)

    if days_remaining <= DAILY_WARN_THRESHOLD or days_remaining in WARN_DAYS:
        if days_remaining <= DAILY_WARN_THRESHOLD:
            emoji = ":rotating_light:"
        elif days_remaining <= 14:
            emoji = ":warning:"
        else:
            emoji = ":bell:"

        post_slack_message(
            f"{emoji} TUF root metadata expires in *{days_remaining} days* "
            f"(on `{expires_str}`). "
            f"Time to rotate: `{DOWNLOADER_ROOT}`"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            post_slack_message(f":x: TUF root check failed with an unexpected error: `{e}`")
        except Exception:
            pass
        raise
