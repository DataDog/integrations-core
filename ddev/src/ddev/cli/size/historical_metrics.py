import argparse
import subprocess
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from utils.common_funcs import GitRepo

console = Console()


def upload_historical_metrics(date_from_str: str, org: str) -> None:
    current_path = Path(__file__).resolve()
    repo_path = current_path.parents[5]

    date_from = datetime.strptime(date_from_str, "%Y-%m-%d")
    min_date = datetime.strptime("2024-09-18", "%Y-%m-%d")

    if date_from < min_date:
        raise ValueError(f"Date ({date_from}) must be after 2024-09-18")
    try:
        console.print(f"[green]Processing repository: {repo_path}")
        with GitRepo(repo_path) as gitRepo:
            commits = gitRepo._run(f"git log --pretty=format:%H --since='{date_from}'")
            console.print(f"Found {len(commits)} commits to process")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
                console=console,
            ) as progress:
                commit_task = progress.add_task("[cyan]Processing commits...")

                for i, commit in enumerate(commits, 1):
                    date, _, _ = gitRepo.get_commit_metadata(commit)
                    progress.update(
                        commit_task, description=f"Processing commit {i}/{len(commits)}: {commit[:8]} ({date})"
                    )
                    print(f"Processing commit {i}/{len(commits)}: {commit[:8]} ({date})", flush=True)
                    gitRepo.checkout_commit(commit)
                    result = subprocess.run(
                        ["ddev", "--here", "size", "status", "--to-dd-org", org],
                        cwd=gitRepo.repo_dir,
                        text=True,
                        capture_output=True,
                    )
                    if result.returncode != 0:
                        console.print(f"[red]Error in commit {commit}: {result.stderr}")
                        continue

                    result = subprocess.run(
                        ["ddev", "--here", "size", "status", "--compressed", "--to-dd-org", org],
                        text=True,
                        cwd=gitRepo.repo_dir,
                        capture_output=True,
                    )

                    if result.returncode != 0:
                        console.print(f"[red]Error in commit {commit}: {result.stderr}")
                        continue

                    progress.advance(commit_task)
                progress.update(commit_task, description="[green]All commits processed!")

    except KeyboardInterrupt:
        console.print("[red]Process interrupted by user.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Upload historical metrics to Datadog')
    parser.add_argument('--date-from', help='Start date in YYYY-MM-DD format')
    parser.add_argument('--org', default='default', help='Organization name')

    args = parser.parse_args()
    date_from = args.date_from
    org = args.org
    upload_historical_metrics(date_from, org)
