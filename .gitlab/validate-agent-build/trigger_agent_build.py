import requests
import os
import argparse


DATADOG_AGENT_PIPELINE_URL = os.environ['DATADOG_AGENT_PIPELINE_URL'].rstrip('/')
BASE_URL = os.environ['CI_API_V4_URL']
CI_TOKEN = os.environ['CI_JOB_TOKEN']


def trigger_pipeline():
    # TODO: Opt out of kitchen tests when the appropriate flag is implemented.
    data = {
        "token": CI_TOKEN,
        "ref": "master",
        "variables": {
            "RELEASE_VERSION_6": "nightly",
            "RELEASE_VERSION_7": "nightly-a7",
            "DEB_RPM_BUCKET_BRANCH": "none",
            "INTEGRATIONS_CORE_VERSION": os.environ['CI_COMMIT_REF_NAME'],
            "RUN_KITCHEN_TESTS": "false",
        }
    }

    print("Creating child pipeline with params: %s", data['variables'])
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

