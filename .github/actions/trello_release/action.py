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

# Retrieve the github environment from the docker runtime Github Actions provides
# https://developer.github.com/actions/creating-github-actions/accessing-the-runtime-environment/
def get_github_event():
    event_file_path = os.environ[EVENT_PATH_ENV_VAR]
    try:
        with open(event_file_path, "r") as f:
            pull_request_event = f.read()
        return json.loads(pull_request_event)
    except (IOError, ValueError) as e:
        emit_dd_event(FAILED, f"Unable to create Trello card: {e}")
        raise

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
    try:
        response = requests.post(TRELLO_API_URL, params=querystring)
        response.raise_for_status()
    except Exception as e:
        emit_dd_event(FAILED, f"Couldn't submit card to Trello API: {e}")
        raise e

# Use the github labels from the PR to determine if we should create a Trello card
# True if any of the labels on the PR starts with changelog and isn't `no-changelog`
# AND the PR is merged
def should_create_card(pull_request_event):
    pr_includes_changes = False
    pr_is_merged = False

    for label in pull_request_event.get('pull_request').get('labels', []):
        label = label.get('name', '')
        if label.startswith('changelog/') and label != 'changelog/no-changelog':
            pr_includes_changes = True

    if pull_request_event.get('merged') and pull_request_event.get('action') == 'closed':
        pr_is_merged = True

    return pr_includes_changes and pr_is_merged

if __name__ == "__main__":
    validate_env_vars()
    pull_request_event = get_github_event()
    pr_url = pull_request_event.get('pull_request').get('url')
    if should_create_card(pull_request_event):
        try:
            create_trello_card(pull_request_event.get('pull_request'))
        else:
            emit_dd_event(SUCCESS, f"Succesfully created Trello card for PR {pr_url}")
    else:
        print(f"Not creating a card for Pull Request {pr_url}")
