"""Post a 'wheel release starting' Slack notification via chat.postMessage.

Env: SLACK_API_TOKEN, SLACK_CHANNEL_ID (both required or no-op), SOURCE_REPO,
REF, PACKAGES, RUN_URL.

Error handling distinguishes two failure classes so a broken token is never
silently swallowed as a green run:

* Persistent misconfigurations (missing OAuth scope, bad/expired token, wrong
  channel, bot not in channel) recur on every release. They are reported to the
  GitHub step summary and fail the step so they get fixed immediately. This is
  safe because the notify job is not a dependency of the release itself.
* Transient problems (network, timeout, 5xx, rate limiting) only warn and never
  fail the job, so a momentary Slack blip does not create release noise.
"""
import json
import os
import sys
import urllib.error
import urllib.request

SLACK_URL = "https://slack.com/api/chat.postMessage"

# Slack API `error` codes that mean the notifier is misconfigured rather than
# hitting a transient blip. These will fail on every release until fixed.
CONFIG_ERRORS = frozenset(
    {
        "missing_scope",
        "invalid_auth",
        "not_authed",
        "token_revoked",
        "account_inactive",
        "channel_not_found",
        "not_in_channel",
    }
)


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


def report_config_error(error: str) -> None:
    """Surface a persistent misconfiguration loudly in the GitHub step summary."""
    message = (
        f"Slack notification misconfigured: `{error}`. The pending-release message was NOT delivered. "
        "Verify SLACK_API_TOKEN has the `chat:write` scope and is valid, and that the bot is a member "
        "of SLACK_CHANNEL_ID."
    )
    print(f"::error::{message}")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(f"### \u274c Slack notification failed\n\n{message}\n")


def post(token: str, channel: str, text: str) -> bool:
    """Post *text* to *channel*; return False only on a persistent misconfiguration.

    Success and transient failures return True (transient ones only warn), so the
    caller fails the step exclusively for config errors that need a human fix.
    """
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
        print(f"::warning::Slack request failed (transient): {e}")
        return True
    if body.get("ok"):
        return True
    error = body.get("error", "unknown error")
    if error in CONFIG_ERRORS:
        report_config_error(error)
        return False
    print(f"::warning::Slack notification failed: {error}")
    return True


def main() -> None:
    token = os.environ.get("SLACK_API_TOKEN", "").strip()
    channel = os.environ.get("SLACK_CHANNEL_ID", "").strip()
    if not token or not channel:
        print("Slack token or channel not configured; skipping notification.")
        return
    delivered = post(
        token,
        channel,
        build_text(
            os.environ.get("SOURCE_REPO", "integrations-core"),
            os.environ.get("REF", ""),
            os.environ.get("PACKAGES", ""),
            os.environ.get("RUN_URL", ""),
        ),
    )
    if not delivered:
        sys.exit(1)


if __name__ == "__main__":
    main()
