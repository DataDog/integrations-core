import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

AGENT_REPO = "DataDog/datadog-agent"
RELEASE_JSON_URL = f"https://raw.githubusercontent.com/{AGENT_REPO}/main/release.json"
COMMITS_API_URL = f"https://api.github.com/repos/{AGENT_REPO}/commits"
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]


def fetch_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def get_integrations_core_version(sha):
    raw_url = f"https://raw.githubusercontent.com/{AGENT_REPO}/{sha}/release.json"
    req = urllib.request.Request(raw_url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    with urllib.request.urlopen(req) as resp:
        release = json.loads(resp.read().decode())
    return release["dependencies"]["INTEGRATIONS_CORE_VERSION"]


# Step 1: get current pin
req = urllib.request.Request(RELEASE_JSON_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
with urllib.request.urlopen(req) as resp:
    release_data = json.loads(resp.read().decode())
current_pin = release_data["dependencies"]["INTEGRATIONS_CORE_VERSION"]
print(f"Current pin: {current_pin}")

# Steps 2 & 3: fetch commits to release.json from the last month, walk newest→oldest.
# release.json is updated for many reasons beyond the integrations-core pin, so we bound by
# time window rather than a fixed page count. If the pin has been unchanged for the full month,
# last_pin_commit will hold the oldest commit in the window (a conservative undercount, but
# still well above the 4-day alert threshold).
since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
last_pin_commit: dict | None = None
pin_changed = False
page = 1

while not pin_changed:
    page_commits = fetch_json(
        f"{COMMITS_API_URL}?path=release.json&per_page=100&since={since}&page={page}",
        headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"},
    )
    if not page_commits:
        break
    print(f"Page {page}: fetched {len(page_commits)} commits touching release.json")
    if last_pin_commit is None:
        last_pin_commit = page_commits[0]  # most recent commit, used as fallback
    for commit in page_commits:
        sha = commit["sha"]
        try:
            pin_at_sha = get_integrations_core_version(sha)
        except Exception as e:
            print(f"Error: could not fetch release.json at {sha}: {e}")
            raise  # fail the job; don't submit a potentially wrong metric
        if pin_at_sha == current_pin:
            last_pin_commit = commit
        else:
            pin_changed = True
            break  # last_pin_commit is the oldest commit still on the current pin
    page += 1

# Step 4: compute days
now_utc = datetime.now(timezone.utc)
if last_pin_commit is None:
    # No commits to release.json in the last 30 days — pin is at least 30 days old
    days = 30
    print("No commits to release.json found in the last 30 days; reporting days=30")
else:
    committed_at_str = last_pin_commit["commit"]["committer"]["date"]
    committed_at = datetime.fromisoformat(committed_at_str.replace("Z", "+00:00"))
    days = (now_utc - committed_at).days
    print(f"Last pin commit: {last_pin_commit['sha']} at {committed_at_str}")
    print(f"Days since last pin: {days}")

# Write days to GITHUB_OUTPUT for the submit step
github_output = os.environ.get("GITHUB_OUTPUT")
if github_output:
    with open(github_output, "a") as f:
        f.write(f"days={days}\n")
