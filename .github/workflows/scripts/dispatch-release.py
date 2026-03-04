"""Send a repository_dispatch event to agent-integration-wheels-release.

Required environment variables:
  GH_TOKEN      short-lived token from dd-octo-sts
  INTEGRATIONS  JSON array of integration names
  SOURCE_REPO   source repository name (e.g. integrations-core)
  REF           commit SHA or ref to build from
"""
import json
import os
import urllib.request

payload = json.dumps(
    {
        "event_type": "build-integrations",
        "client_payload": {
            "integrations": json.loads(os.environ["INTEGRATIONS"]),
            "source_repo": os.environ["SOURCE_REPO"],
            "source_repo_ref": os.environ["REF"],
        },
    }
).encode()

req = urllib.request.Request(
    "https://api.github.com/repos/DataDog/agent-integration-wheels-release/dispatches",
    data=payload,
    headers={
        "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    },
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    print(f"Dispatched: HTTP {resp.status}")
