import argparse
import sys
import time

import requests
import os

DATADOG_AGENT_PIPELINE_URL = os.environ['DATADOG_AGENT_PIPELINE_URL'].rstrip('/')
BASE_URL = os.environ['CI_API_V4_URL']
GITLAB_TOKEN = os.environ['GITLAB_TOKEN']
STAGES_TO_CHECK = ['deps_fetch', 'source_test', 'binary_build', 'package_build']


def _get_jobs(pipeline_id, scope=None):
    all_jobs = []
    url = f"{DATADOG_AGENT_PIPELINE_URL}/pipelines/{pipeline_id}/jobs"
    while True:
        resp = requests.get(url, headers={'PRIVATE-TOKEN': GITLAB_TOKEN}, params={"per_page": 20, "scope": scope})
        resp.raise_for_status()
        all_jobs.extend(resp.json())
        if 'next' not in resp.links:
            break

        url = resp.links['next']['url']

    return all_jobs


def get_pending_jobs(pipeline_id):
    scopes = ['created', 'pending', 'running']
    all_jobs = []
    for scope in scopes:
        all_jobs.extend(_get_jobs(pipeline_id, scope=scope))

    jobs = [j for j in all_jobs if j['stage'] in STAGES_TO_CHECK]
    return jobs


def get_failed_jobs(pipeline_id):
    scopes = ['failed', 'canceled']
    jobs = []
    for scope in scopes:
        jobs.extend(_get_jobs(pipeline_id, scope=scope))

    jobs = [j for j in jobs if not j['allow_failure'] and j['stage'] in STAGES_TO_CHECK]
    return jobs


def retry_failed_jobs(pipeline_id):
    failed_jobs = get_failed_jobs(pipeline_id)
    print(f"Found {len(failed_jobs)} failed jobs. Retrying...")
    for job in failed_jobs:
        url = f"{DATADOG_AGENT_PIPELINE_URL}/jobs/{job['id']}/retry"
        resp = requests.post(url, headers={'PRIVATE-TOKEN': GITLAB_TOKEN})
        resp.raise_for_status()
        print(f"Retried job: {job['id']}")
    print("All jobs retried")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Wait for (and retry if needed) a given agent build pipeline.')
    parser.add_argument('-p', '--pipeline-id', dest='pipeline_id', action='store',
                        help='The pipeline id to watch for.', required=True)

    args = parser.parse_args()
    pipeline_id = args.pipeline_id

    # If the pipeline already exists (maybe when this job is retried), then retry all failed jobs.
    retry_failed_jobs(pipeline_id)

    # Wait for jobs to end and exit immediately if any failure.
    while True:
        pending_jobs = get_pending_jobs(pipeline_id)
        if not pending_jobs:
            print("Success, pipeline has built the agent correctly.")
            break

        print(f"Still {len(pending_jobs)} are pending...")
        failed_jobs = get_failed_jobs(pipeline_id)
        if failed_jobs:
            for job in failed_jobs:
                print(f"ERROR: Job {job['web_url']} has encountered a failure, exiting.")
            sys.exit(1)
        print("Waiting 1 min before next check.")
        time.sleep(60)



