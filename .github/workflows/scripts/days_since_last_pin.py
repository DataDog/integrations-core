import json
import os
import urllib.request
from datetime import datetime, timezone

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

# Step 2: fetch recent commits to release.json
# 30 commits covers many months of bi-weekly pins; pin unchanged across all 30 is extremely unlikely
commits_url = f"{COMMITS_API_URL}?path=release.json&per_page=30"
commits = fetch_json(commits_url, headers={
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
})
print(f"Fetched {len(commits)} commits touching release.json")

# Step 3: walk commits newest→oldest to find when the pin last changed
last_pin_commit = commits[0]
for commit in commits:
    sha = commit["sha"]
    try:
        pin_at_sha = get_integrations_core_version(sha)
    except Exception as e:
        print(f"Error: could not fetch release.json at {sha}: {e}")
        raise  # fail the job; don't submit a potentially wrong metric
    if pin_at_sha == current_pin:
        last_pin_commit = commit
    else:
        break  # pin changed here — last_pin_commit is correct

# Step 4: compute days
committed_at_str = last_pin_commit["commit"]["committer"]["date"]
committed_at = datetime.fromisoformat(committed_at_str.replace("Z", "+00:00"))
now_utc = datetime.now(timezone.utc)
days = (now_utc - committed_at).days
print(f"Last pin commit: {last_pin_commit['sha']} at {committed_at_str}")
print(f"Days since last pin: {days}")

# Write days to GITHUB_OUTPUT for the submit step
github_output = os.environ.get("GITHUB_OUTPUT")
if github_output:
    with open(github_output, "a") as f:
        f.write(f"days={days}\n")
