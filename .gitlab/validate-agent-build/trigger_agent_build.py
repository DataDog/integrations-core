import requests
import os
import argparse


DATADOG_AGENT_PIPELINE_URL = os.environ['DATADOG_AGENT_PIPELINE_URL'].rstrip('/')
RELEASE_BRANCH = os.environ['RELEASE_BRANCH']
BASE_URL = os.environ['CI_API_V4_URL']
CI_TOKEN = os.environ['CI_JOB_TOKEN']


def trigger_pipeline():
    trigger_ref = RELEASE_BRANCH

    # Search for the release branch in the datadog-agent repository
    r = requests.get(f"https://api.github.com/repos/DataDog/datadog-agent/branches/{RELEASE_BRANCH}")

    if r.status_code != 200:
        print(f"Tag '{RELEASE_BRANCH}' is not a release tag, falling back to main")
        trigger_ref = "main"
    data = {
        "token": CI_TOKEN,
        "ref": trigger_ref,
        "variables": {
            "RELEASE_VERSION_6": "nightly",
            "RELEASE_VERSION_7": "nightly-a7",
            "BUCKET_BRANCH": "dev",
            "DEPLOY_AGENT": "false",
            "INTEGRATIONS_CORE_VERSION": os.environ['CI_COMMIT_REF_NAME'],
            # disable kitchen tests
            "RUN_KITCHEN_TESTS": "false",
            # disable e2e tests
            "RUN_E2E_TESTS": "off",
        }
    }

    print(f"Creating child pipeline with params: {data.get('variables')} off branch: {trigger_ref}")
    res = requests.post(f"{DATADOG_AGENT_PIPELINE_URL}/trigger/pipeline", json=data)
    res.raise_for_status()
    child_pipeline = res.json()
    print(f"Created a datadog-agent pipeline with id={child_pipeline['id']}, url={child_pipeline['web_url']}")
    return child_pipeline['id']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Trigger an agent build on gitlab.')
    parser.add_argument('-o', '--output-file', dest='output_file', action='store',
                        help='The file on which to write the pipeline id.', required=True)

    args = parser.parse_args()
    output_file = args.output_file
    pipeline_id = trigger_pipeline()
    with open(output_file, 'w') as f:
        f.write(str(pipeline_id))

