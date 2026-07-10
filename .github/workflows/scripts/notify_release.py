"""Trigger the 'Wheels Release Pipeline Notification' Datadog workflow.

The Datadog workflow owns delivery (Slack connection, retries, run history);
this script renders the message and triggers the workflow's API trigger via
POST /api/v2/workflows/{id}/instances. Credentials are minted in CI by dd-sts
(DD-API-KEY + a DD-APPLICATION-KEY with Actions API access).

Env: DD_API_KEY, DD_APP_KEY, DD_WORKFLOW_ID (all required or no-op), DD_SITE
(default datadoghq.com), SOURCE_REPO, REF, PACKAGES, RUN_URL.

Error handling keeps a misconfiguration from passing as a green run:

* Persistent problems (bad/expired keys, missing scope, wrong workflow id,
  rejected payload — HTTP 4xx) are reported to the GitHub step summary and fail
  the step. This is safe because the notify job is not a dependency of the
  release itself.
* Transient problems (network, timeout, 5xx, HTTP 429) only warn and never fail
  the job, so a momentary blip does not create release noise.
"""
import json
import os
import sys
import urllib.error
import urllib.request


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
        "Verify the dd-sts credentials (DD-APPLICATION-KEY with Actions API access), DD_WORKFLOW_ID, "
        "and DD_SITE."
    )
    print(f"::error::{message}")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(f"### \u274c Release notification failed\n\n{message}\n")


def post(api_url: str, api_key: str, app_key: str, payload: dict) -> bool:
    """Trigger the workflow; return False only on a persistent misconfiguration.

    Success and transient failures return True (transient ones only warn), so the
    caller fails the step exclusively for problems that need a human fix.
    """
    data = json.dumps({"meta": {"payload": payload}}).encode()
    request = urllib.request.Request(
        api_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": app_key,
        },
    )
    try:
        urllib.request.urlopen(request, timeout=15).close()
    except urllib.error.HTTPError as e:
        if e.code == 429 or e.code >= 500:
            print(f"::warning::Release notification failed (transient): HTTP {e.code}")
            return True
        report_config_error(f"HTTP {e.code}")
        return False
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        print(f"::warning::Release notification request failed (transient): {e}")
        return True
    return True


def main() -> None:
    api_key = os.environ.get("DD_API_KEY", "").strip()
    app_key = os.environ.get("DD_APP_KEY", "").strip()
    workflow_id = os.environ.get("DD_WORKFLOW_ID", "").strip()
    if not (api_key and app_key and workflow_id):
        print("Datadog workflow credentials not configured; skipping notification.")
        return
    site = os.environ.get("DD_SITE", "").strip() or "datadoghq.com"
    source_repo = os.environ.get("SOURCE_REPO", "integrations-core")
    ref = os.environ.get("REF", "")
    packages = os.environ.get("PACKAGES", "")
    run_url = os.environ.get("RUN_URL", "")
    payload = {
        "text": build_text(source_repo, ref, packages, run_url),
        "state": "pending",
        "repository": source_repo,
        "ref": ref,
        "packages": packages,
        "run_url": run_url,
    }
    api_url = f"https://api.{site}/api/v2/workflows/{workflow_id}/instances"
    if not post(api_url, api_key, app_key, payload):
        sys.exit(1)


if __name__ == "__main__":
    main()
