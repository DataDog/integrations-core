# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import json

from datadog import initialize, api
import requests

(
    EVENT_PATH_ENV_VAR,
    TRELLO_LIST_ID,
    TRELLO_KEY_ENV_VAR,
    TRELLO_TOKEN_ENV_VAR,
    DD_API_KEY_ENV_VAR
) = ENV_VARS = (
    'GITHUB_EVENT_PATH',
    'TRELLO_LIST_ID',
    'TRELLO_KEY',
    'TRELLO_TOKEN',
    'DD_API_KEY',
)

CORE_REPO = 'integrations-core'
TRELLO_API_URL = "https://api.trello.com/1/cards"
SUCCESS = "Success"
FAILED = "Failed"

# Make sure all environment variables are present
def validate_env_vars():
    msg = ''
    for var in ENV_VARS:
        if var not in os.environ:
            msg += f"Missing a required environment variable {var}. Cannot create card\n"
    if msg:
        emit_dd_event(FAILED, msg)
        raise Exception(msg)


# Emit an event to Datadog based on whether or not we could create the card
def emit_dd_event(status, msg):
    options = {
        'api_key': os.environ['DD_API_KEY'],
    }
    initialize(**options)

    title = f"Trello Card creation {status}"
    text = msg
    tags = ['team:agent-integrations', 'application:trello_github_action']

    api.Event.create(title=title, text=text, tags=tags)


# Create the Trello card on the board specified by the environment variable
# https://developers.trello.com/reference/#cards-2
def create_trello_card(pull_request_event):
    querystring = {
        "idList": os.environ[TRELLO_LIST_ID_ENV_VAR],
        "keepFromSource":"all",
        "name": pull_request_event.get('title'),
        "description": pull_request_event.get('body', '')[:5000],
        "key": os.environ[TRELLO_KEY_ENV_VAR],
        "token": os.environ[TRELLO_TOKEN_ENV_VAR]
    }

    response = requests.post(TRELLO_API_URL, params=querystring)
    response.raise_for_status()

# Use the github labels from the PR to determine if we should create a Trello card
# True if any of the labels on the PR starts with changelog and isn't `no-changelog`
# AND the PR is merged
def should_create_card(pull_request_event):
    pr_includes_changes = False
    pr_is_merged = False

    for label in pull_request_event.get('labels', []):
        label = label.get('name', '')
        if label.startswith('changelog/') and label != 'changelog/no-changelog':
            pr_includes_changes = True

    with open(os.environ['GITHUB_EVENT_PATH'], 'r') as f:
        github_event = json.loads(f.read())

    if 'master' in github_event.get('ref'):
        pr_is_merged = True

    return pr_includes_changes and pr_is_merged

# Return the first PR found from the provided commit
def get_pr_from_commit(commit_hash):
    response = requests.get(
        f'https://api.github.com/search/issues?q=sha:{commit_hash}+repo:DataDog/{CORE_REPO}+is:merged',
    )
    try:
        response.raise_for_status()
        return response.json().get('items')[0]
    except requests.HTTPError as e:
        emit_dd_event(FAILED, f'Couldn\'t retrieve github PR from commit: {e}')
        raise e
    except IndexError as e:
        print("Couldn't find commit in a PR, likely isn't yet merged")
        return {}

if __name__ == "__main__":
    validate_env_vars()
    pull_request = get_pr_from_commit(os.environ['GITHUB_SHA'])
    pr_url = pull_request.get('url')

    if should_create_card(pull_request):
        try:
            create_trello_card(pull_request_event.get('pull_request'))
        except Exception as e:
            emit_dd_event(FAILED, f"Couldn't submit card to Trello API: {e}")
        else:
            emit_dd_event(SUCCESS, f"Succesfully created Trello card for PR {pr_url}")
    else:
        print(f"Not creating a card for Pull Request {pr_url}")
