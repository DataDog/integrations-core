import argparse
import subprocess
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ddev.cli.size.utils.common_funcs import GitRepo

console = Console(stderr=True)


def upload_historical_metrics(DATE_FROM: str, ORG: str) -> None:
    current_path = Path(__file__).resolve()
    repo_path = current_path.parents[5]

    date_from = datetime.strptime(DATE_FROM, "%Y-%m-%d")
    min_date = datetime.strptime("2024-09-17", "%Y-%m-%d")

    if date_from < min_date:
        raise ValueError(f"Date ({DATE_FROM}) must be after 2024-09-17")
    try:
        console.print(f"[green]Processing repository: {repo_path}")
        with GitRepo(repo_path) as gitRepo:
            commits = gitRepo._run(f"git log --reverse --pretty=format:%H --since={DATE_FROM}")
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
                    progress.update(commit_task, description=f"Processing commit {i}/{len(commits)}: {commit[:8]} ({date})")
                    gitRepo.checkout_commit(commit)

                    result = subprocess.run(
                        ["ddev", "size", "status", "--to-dd-org", ORG],
                        cwd=gitRepo.repo_dir,
                        text=True,
                        capture_output=True,
                    )
                    # print("[UNCOMP STDOUT]", result.stdout)
                    # print("[UNCOMP STDERR]", result.stderr)

                    result = subprocess.run(
                        ["ddev", "size", "status", "--compressed", "--to-dd-org", ORG],
                        cwd=gitRepo.repo_dir,
                        text=True,
                        capture_output=True,
                    )
                    # print("[COMP STDOUT]", result.stdout)
                    # print("[COMP STDERR]", result.stderr)

                    progress.advance(commit_task)
                progress.update(commit_task, description="[green]All commits processed!")
    except KeyboardInterrupt:
        console.print("[red]Process interrupted by user.")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Upload historical metrics to Datadog')
    parser.add_argument('--date-from', help='Start date in YYYY-MM-DD format')
    parser.add_argument('--org', default='default', help='Organization name')

    args = parser.parse_args()
    DATE_FROM = args.date_from
    ORG = args.org
    upload_historical_metrics(DATE_FROM, ORG)
