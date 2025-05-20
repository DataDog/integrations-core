import subprocess

from ddev.cli.size.common import GitRepo
import os 

def upload_historical_metrics():
    url = "/Users/lucia.sanchezbella/dd/integrations-core"
    print(f"Processing repository: {url}")
    with GitRepo(url) as gitRepo:

        commits = gitRepo._run("git log --reverse --pretty=format:%H --since=2025-04-05")
        print(f"Found {len(commits)} commits to process")

        for i, commit in enumerate(commits, 1):
            date, _, _ = gitRepo.get_commit_metadata(commit)
            print(f"Processing commit {i}/{len(commits)}: {commit} ({date})")
            gitRepo.checkout_commit(commit)
            timestamp = get_last_commit_timestamp(gitRepo.repo_dir)
            print("Running uncompressed size metrics...")
            result = subprocess.run(
                ["ddev", "size", "status", "--send-metrics-dd-org", "default", "--timestamp", str(timestamp)],
                cwd=gitRepo.repo_dir,
                text=True,
                capture_output=True,
            )
            print("[UNCOMP STDOUT]", result.stdout)
            print("[UNCOMP STDERR]", result.stderr)

            print("Running compressed size metrics...")
            result = subprocess.run(
                ["ddev", "size", "status", "--compressed", "--send-metrics-dd-org", "default", "--timestamp", str(timestamp)],
                cwd=gitRepo.repo_dir,
                text=True,
                capture_output=True,
            )
            print("[COMP STDOUT]", result.stdout)
            print("[COMP STDERR]", result.stderr)

            print(f"Finished processing commit {i}\n")

def get_last_commit_timestamp(cwd: str) -> int:
    result = subprocess.run(["git", "log", "-1", "--format=%ct"], capture_output=True, text=True, check=True, cwd=cwd)
    return int(result.stdout.strip())

if __name__ == "__main__":
    upload_historical_metrics()
