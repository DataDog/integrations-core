import json
import os
import re  # noqa: F401


with open(os.environ['GITHUB_EVENT_PATH']) as event_file:
    event = json.load(event_file)

    pr_labels = event['pull_request']['labels']

    changelog_labels = list(filter(lambda label: label['name'].startswith(r'changelog/'), pr_labels))

    labels_string = ', '.join([label['name'] for label in changelog_labels])
    print('Current changelog labels: {}'.format(labels_string))

    if len(changelog_labels) == 0:
        raise Exception('There is no changelog label.')
    if len(changelog_labels) > 1:
        raise Exception('There is more than one changelog label.')

    print("Success! There is exactly one changelog label")
