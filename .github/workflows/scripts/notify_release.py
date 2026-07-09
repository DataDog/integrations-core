"""Post a 'wheel release pending' notification to a Datadog Workflow webhook.

The Datadog workflow owns the delivery (Slack connection, retries, run
history), so this script only builds the message and hands a JSON payload to
the workflow's inbound webhook trigger.

Env: DD_WORKFLOW_WEBHOOK_URL (required or no-op), DD_WORKFLOW_WEBHOOK_TOKEN
(optional bearer auth for the trigger), SOURCE_REPO, REF, PACKAGES, RUN_URL.

Error handling mirrors the Slack notifier: a persistent misconfiguration must
not be swallowed as a green run.

* Persistent problems (bad/missing webhook URL or token, rejected payload —
  HTTP 4xx) are reported to the GitHub step summary and fail the step so they
  get fixed immediately. This is safe because the notify job is not a
  dependency of the release itself.
* Transient problems (network, timeout, 5xx, HTTP 429) only warn and never fail
  the job, so a momentary blip does not create release noise.
"""
import json
import os
import sys
import urllib.error
import urllib.request

# HTTP status codes that are retriable/transient rather than a misconfiguration.
TRANSIENT_STATUSES = frozenset({408, 429})


def build_text(source_repo: str, ref: str, packages: str, run_url: str) -> str:
    """Return the release notification message body."""
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
        f"Release notification misconfigured: {error}. The pending-release message was NOT delivered. "
        "Verify DD_WORKFLOW_WEBHOOK_URL points at the workflow's inbound webhook trigger and that "
        "DD_WORKFLOW_WEBHOOK_TOKEN (if the trigger requires it) is valid."
    )
    print(f"::error::{message}")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(f"### \u274c Release notification failed\n\n{message}\n")


def post(url: str, token: str, source_repo: str, ref: str, packages: str, run_url: str) -> bool:
    """Send the payload to the Datadog webhook; return False only on a config error.

    Success and transient failures return True (transient ones only warn), so the
    caller fails the step exclusively for problems that need a human fix.
    """
    payload = {
        "text": build_text(source_repo, ref, packages, run_url),
        "source_repo": source_repo,
        "ref": ref,
        "packages": packages,
        "run_url": run_url,
    }
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    try:
        urllib.request.urlopen(request, timeout=15).close()
    except urllib.error.HTTPError as e:
        if e.code in TRANSIENT_STATUSES or e.code >= 500:
            print(f"::warning::Release notification failed (transient): HTTP {e.code}")
            return True
        report_config_error(f"HTTP {e.code}")
        return False
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        print(f"::warning::Release notification request failed (transient): {e}")
        return True
    return True


def main() -> None:
    url = os.environ.get("DD_WORKFLOW_WEBHOOK_URL", "").strip()
    if not url:
        print("Datadog workflow webhook not configured; skipping notification.")
        return
    delivered = post(
        url,
        os.environ.get("DD_WORKFLOW_WEBHOOK_TOKEN", "").strip(),
        os.environ.get("SOURCE_REPO", "integrations-core"),
        os.environ.get("REF", ""),
        os.environ.get("PACKAGES", ""),
        os.environ.get("RUN_URL", ""),
    )
    if not delivered:
        sys.exit(1)


if __name__ == "__main__":
    main()
