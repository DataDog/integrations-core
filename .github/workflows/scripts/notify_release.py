"""Send a rendered release notification through a Datadog workflow.

Environment variables: DD_API_KEY, DD_APP_KEY, DD_WORKFLOW_ID, DD_SITE,
SOURCE_REPO, REF, PACKAGES, RUN_URL.
"""
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request


def escape_slack_text(value: str) -> str:
    """Escape dynamic text for Slack mrkdwn."""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_packages(packages: str) -> str:
    """Return a readable package list without failing on malformed input."""
    raw_packages = packages.strip()
    if not raw_packages:
        return "auto-detect from tags at HEAD"
    try:
        parsed_packages = json.loads(raw_packages)
    except json.JSONDecodeError:
        return escape_slack_text(raw_packages)
    if not isinstance(parsed_packages, list):
        return escape_slack_text(raw_packages)
    if not parsed_packages:
        return "auto-detect from tags at HEAD"
    return ", ".join(escape_slack_text(str(package)) for package in parsed_packages)


def build_text(source_repo: str, ref: str, packages: str, run_url: str) -> str:
    """Return the release notification message body."""
    return (
        ":hourglass_flowing_sand: *Approve wheel release*\n"
        f"`{escape_slack_text(source_repo)}` · `{escape_slack_text(ref[:12] or '—')}` · "
        f"{format_packages(packages)}\n"
        f"<{run_url}|Review and approve →>"
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


RETRY_DELAYS = (2, 4, 8, 16)
TRANSIENT_HTTP_STATUSES = frozenset({408, 429})


def post(api_url: str, api_key: str, app_key: str, text: str) -> bool:
    """Trigger the workflow; return False only on a persistent misconfiguration."""
    data = json.dumps({"meta": {"payload": {"text": text}}}).encode()
    request = urllib.request.Request(
        api_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": app_key,
        },
    )
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            urllib.request.urlopen(request, timeout=15).close()
        except urllib.error.HTTPError as e:
            is_transient = e.code in TRANSIENT_HTTP_STATUSES or e.code >= 500
            # dd-sts registers new application keys with the Actions API before
            # returning them, but authorization reads can briefly lag that write.
            if (e.code == 403 or is_transient) and attempt < len(RETRY_DELAYS):
                delay = RETRY_DELAYS[attempt]
                print(f"::warning::Release notification received HTTP {e.code}; retrying in {delay} seconds")
                time.sleep(delay)
                continue
            if is_transient:
                print(f"::warning::Release notification failed (transient): HTTP {e.code}")
                return True
            report_config_error(f"HTTP {e.code}")
            return False
        except (OSError, http.client.HTTPException, ValueError) as e:
            if attempt < len(RETRY_DELAYS):
                delay = RETRY_DELAYS[attempt]
                print(f"::warning::Release notification request failed: {e}; retrying in {delay} seconds")
                time.sleep(delay)
                continue
            print(f"::warning::Release notification request failed (transient): {e}")
            return True
        return True
    raise AssertionError("unreachable")


def main() -> None:
    api_key = os.environ.get("DD_API_KEY", "").strip()
    app_key = os.environ.get("DD_APP_KEY", "").strip()
    workflow_id = os.environ.get("DD_WORKFLOW_ID", "").strip()
    missing_config = [
        name
        for name, value in (("DD_API_KEY", api_key), ("DD_APP_KEY", app_key), ("DD_WORKFLOW_ID", workflow_id))
        if not value
    ]
    if missing_config:
        report_config_error(f"missing required configuration: {', '.join(missing_config)}")
        sys.exit(1)
    site = os.environ.get("DD_SITE", "").strip() or "datadoghq.com"
    text = build_text(
        os.environ.get("SOURCE_REPO", "integrations-core"),
        os.environ.get("REF", ""),
        os.environ.get("PACKAGES", ""),
        os.environ.get("RUN_URL", ""),
    )
    api_url = f"https://api.{site}/api/v2/workflows/{workflow_id}/instances"
    if not post(api_url, api_key, app_key, text):
        sys.exit(1)


if __name__ == "__main__":
    main()
