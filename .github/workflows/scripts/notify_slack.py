"""Post a 'wheel release starting' Slack notification via chat.postMessage.

Env: SLACK_API_TOKEN, SLACK_CHANNEL_ID (both required or no-op), SOURCE_REPO,
REF, PACKAGES, RUN_URL. Slack/network errors warn and never fail the job.
"""
import json
import os
import urllib.error
import urllib.request

SLACK_URL = "https://slack.com/api/chat.postMessage"


def build_text(source_repo: str, ref: str, packages: str, run_url: str) -> str:
    """Return the release notification Slack message body."""
    # TODO: this fires before the approval gate, so the release is pending. Once
    # the `release` environment gate is removed, reword to "Wheel release starting"
    # with a "View release run" link, since the release will start immediately.
    return (
        f":hourglass_flowing_sand: *Wheel release pending approval* — `{source_repo}`\n"
        f"• ref: `{ref[:12] or '—'}`\n"
        f"• packages: {packages.strip() or 'auto-detect from tags at HEAD'}\n"
        f"• <{run_url}|Review &amp; approve →>"
    )


def post(token: str, channel: str, text: str) -> None:
    """Post *text* to *channel*, warning (not failing) on error."""
    data = json.dumps({"channel": channel, "text": text, "unfurl_links": False}).encode()
    request = urllib.request.Request(
        SLACK_URL,
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        print(f"::warning::Slack request failed: {e}")
        return
    if not body.get("ok"):
        print(f"::warning::Slack notification failed: {body.get('error', 'unknown error')}")


def main() -> None:
    token = os.environ.get("SLACK_API_TOKEN", "").strip()
    channel = os.environ.get("SLACK_CHANNEL_ID", "").strip()
    if not token or not channel:
        print("Slack token or channel not configured; skipping notification.")
        return
    post(
        token,
        channel,
        build_text(
            os.environ.get("SOURCE_REPO", "integrations-core"),
            os.environ.get("REF", ""),
            os.environ.get("PACKAGES", ""),
            os.environ.get("RUN_URL", ""),
        ),
    )


if __name__ == "__main__":
    main()
