"""Check TUF root metadata: verify local file matches remote and warn when close to expiring."""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REMOTE_URL = "https://dd-integrations-core-wheels-build-stable.datadoghq.com/metadata.staged/root.json"
LOCAL_PATH = Path("datadog_checks_downloader/datadog_checks/downloader/data/repo/metadata/root.json")

WARN_DAYS = [60, 30, 14]
DAILY_WARN_THRESHOLD = 10

SLACK_API_TOKEN = os.environ["SLACK_API_TOKEN"]
SLACK_CHANNEL_IDS = os.environ["SLACK_CHANNEL_IDS"].split(",")
DEBUG_RUN = os.environ.get("DEBUG_RUN", "").lower() == "true"


def fetch_remote() -> dict:
    with urllib.request.urlopen(REMOTE_URL) as resp:
        return json.loads(resp.read().decode())


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
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
            if not result.get("ok"):
                print(f"Slack error for channel {channel_id}: {result.get('error')}", file=sys.stderr)


def should_warn(days_remaining: int) -> bool:
    if days_remaining <= DAILY_WARN_THRESHOLD:
        return True
    return days_remaining in WARN_DAYS


def main() -> None:
    errors: list[str] = []

    remote = fetch_remote()
    local = json.loads(LOCAL_PATH.read_text())

    if local != remote:
        errors.append(
            f":x: TUF root mismatch: `{LOCAL_PATH}` does not match `{REMOTE_URL}`. "
            "The local file needs to be updated."
        )

    expires_str = local["signed"]["expires"]
    expires = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    days_remaining = (expires - now).days

    print(f"TUF root expires: {expires_str} ({days_remaining} days remaining)")

    if DEBUG_RUN:
        match_status = ":white_check_mark: Local and remote `root.json` match." if not errors else ":x: Local and remote `root.json` do *not* match."
        post_slack_message(
            f":ladybug: *Debug run*\n"
            f"{match_status}\n"
            f"Metadata expires on `{expires_str}` ({days_remaining} days remaining)."
        )
        return

    if errors:
        post_slack_message("\n".join(errors))
        sys.exit(1)

    if should_warn(days_remaining):
        if days_remaining <= DAILY_WARN_THRESHOLD:
            emoji = ":rotating_light:"
        elif days_remaining <= 14:
            emoji = ":warning:"
        else:
            emoji = ":bell:"

        message = (
            f"{emoji} TUF root metadata expires in *{days_remaining} days* "
            f"(on `{expires_str}`). "
            "Time to rotate: `datadog_checks_downloader/datadog_checks/downloader/data/repo/metadata/root.json`"
        )
        post_slack_message(message)


if __name__ == "__main__":
    main()
