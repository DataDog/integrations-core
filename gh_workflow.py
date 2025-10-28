#!/usr/bin/env python3
"""
Trigger GitHub workflow with matrix jobs grouped by target.
Each target gets its own workflow dispatch with all its jobs.

Usage Examples:
  # Dry run with first 10 jobs
  python gh_workflow.py --dry-run --limit 10

  # Run on current branch (will report as PR check if on PR branch)
  python gh_workflow.py --ref HEAD

  # Run on specific PR (get SHA from PR page)
  python gh_workflow.py --ref abc123def456...

  # Run on master (default)
  python gh_workflow.py

How PR Checks Work:
  When you specify a ref that matches a PR's head SHA, GitHub automatically
  associates the workflow run with that PR and shows it as a status check.

  To get the PR head SHA:
  - Use --ref HEAD when on the PR branch
  - Or get it from: gh pr view <PR_NUMBER> --json headRefOid -q .headRefOid
"""
import argparse
import json
import subprocess
import sys
from collections import defaultdict


def get_current_sha() -> str:
    """Get the current git commit SHA."""
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()


def get_matrix_jobs(limit: int | None = None) -> list[dict]:
    """Get the CI matrix jobs from the ci_matrix.py script."""
    result = subprocess.run(
        ['python', 'ddev/src/ddev/utils/scripts/ci_matrix.py', '--all'],
        capture_output=True,
        text=True,
        check=True
    )

    jobs = json.loads(result.stdout)

    if limit:
        jobs = jobs[:limit]

    return jobs


def group_jobs_by_target(jobs: list[dict]) -> dict[str, list[dict]]:
    """Group jobs by their target field."""
    grouped = defaultdict(list)
    for job in jobs:
        target = job['target']
        grouped[target].append(job)
    return dict(grouped)


def trigger_workflow(target: str, jobs: list[dict], ref: str, dry_run: bool = False) -> bool:
    """Trigger the GitHub workflow for a specific target with its jobs."""
    matrix_json = json.dumps(jobs)

    if dry_run:
        print(f"\n[DRY RUN] Would trigger workflow for target: {target}")
        print(f"  Number of jobs: {len(jobs)}")
        print(f"  Matrix size: {len(matrix_json)} bytes")
        print(f"  Ref: {ref}")
        print(f"  Jobs: {', '.join(job['name'] for job in jobs)}")
        return True

    cmd = [
        'gh', 'api',
        '--method', 'POST',
        '-H', 'Accept: application/vnd.github+json',
        '-H', 'X-GitHub-Api-Version: 2022-11-28',
        '/repos/DataDog/integrations-core/actions/workflows/zz-test-worker-poc.yaml/dispatches',
        '-f', f'inputs[matrix_json]={matrix_json}',
        '-f', f'inputs[ref]={ref}'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✓ Triggered workflow for target: {target} ({len(jobs)} jobs)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to trigger workflow for target: {target}", file=sys.stderr)
        print(f"  Error: {e.stderr}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Trigger GitHub workflows with matrix jobs grouped by target'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit total number of jobs to process'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print what would be done without actually triggering workflows'
    )
    parser.add_argument(
        '--ref',
        default='master',
        help='Git ref to run workflows on (branch, tag, or SHA). Use "HEAD" for current commit. Use PR head SHA to report as PR check. Default: master'
    )

    args = parser.parse_args()

    # Resolve ref if it's HEAD
    if args.ref == 'HEAD':
        args.ref = get_current_sha()
        print(f"Resolved HEAD to: {args.ref}")

    # Get all matrix jobs
    print("Generating CI matrix...")
    jobs = get_matrix_jobs(limit=args.limit)
    print(f"Total jobs: {len(jobs)}")

    # Group by target
    grouped_jobs = group_jobs_by_target(jobs)
    print(f"Unique targets: {len(grouped_jobs)}")

    if args.dry_run:
        print("\n" + "="*60)
        print("DRY RUN MODE - No workflows will be triggered")
        print("="*60)

    print(f"Using ref: {args.ref}")

    # Trigger workflow for each target
    success_count = 0
    for target, target_jobs in grouped_jobs.items():
        if trigger_workflow(target, target_jobs, args.ref, dry_run=args.dry_run):
            success_count += 1

    print(f"\n{'Would trigger' if args.dry_run else 'Triggered'} {success_count}/{len(grouped_jobs)} targets")

    if success_count < len(grouped_jobs):
        sys.exit(1)


if __name__ == '__main__':
    main()

