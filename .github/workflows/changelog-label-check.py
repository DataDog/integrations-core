import json
import os
import re


try:
    event_file = open(os.environ['GITHUB_EVENT_PATH'])
    event = json.load(event_file)

    pr_labels = event['pull_requests']['labels']

    changelog_labels = list(filter(lambda label: label['name'].startswith(r'changelog/'), pr_labels))
    print("Current changelog labels: {}".format(changelog_labels))

    if len(changelog_labels) == 0:
        raise Exception('There is no changelog label.')
    if len(changelog_labels) > 1:
        raise Exception('There is more than one changelog label.')

    print("Success! There is exactly one changelog label.")

except Exception as e:
    print("Exception when checking the labels")
    raise e
