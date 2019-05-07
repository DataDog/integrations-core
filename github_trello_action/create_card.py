# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import json

from datadog import initialize, api
import requests

EVENT_PATH_ENV_VAR = "GITHUB_EVENT_PATH"
TRELLO_BOARD_LIST_ENV_VAR = "TRELLO_BOARD_LIST"
DD_API_KEY_ENV_VAR = "DD_API_KEY"
TRELLO_API_URL = url = "https://api.trello.com/1/cards"
SUCCESS = "Success"
FAILED = "Failed"

def validate_env_vars():
    ## Make sure all environment variables are present
    try:
        os.environ[EVENT_PATH_ENV_VAR]
        os.environ[TRELLO_BOARD_LIST]
        os.environ[DD_API_KEY]
    except KeyError:
        msg = "Missing a required environment variable. Cannot create event"
        emit_dd_event(FAILED, msg)
        raise


# Emit an event to Datadog based on whether or not we could create the card
def emit_dd_event(status, msg):
    options = {
        'api_key': os.environ['DD_API_KEY'],
    }
    initialize(**options)

    title = "Trello Card creation {}".format(status)
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
        return json.loads(pull_request_event).get('pull_request')
    except (IOError, ValueError) as e:
        emit_dd_event(FAILED, "Unable to create Trello card: {}".format(e))
        raise

## Crerate the Trello card on the board specified by the environment variable
def create_trello_card(pull_request_event):
    querystring = {
        "idList": os.environ[TRELLO_BOARD_LIST_ENV_VAR],
        "keepFromSource":"all",
        "name": pull_request_event.get('title'),
        "description": pull_request_event.get('body')
    }
    try:
        response = requests.request("POST", url, params=querystring)
    except Exception:
        emit_dd_event(FAILED, "Couldn't submit card to Trello API: {}".format(e))
        raise

## Use the github labels from the PR to determine if we should create a Trello card
## True if any of the labels on the PR starts with changelog and isn't `no-changelog`
def should_create_card(pull_request_event):
    labels = [True for name in pull_request_event.get('labels') if name.get('name').startswith('changelog') and not name.get('name') is not 'changelog/no-changelog']
    if any(labels):
        return True
    return False

if __name__ == "main":
    validate_env_vars()
    pull_request_event = get_github_event()
    pr_url = pull_request_event.get('url')
    if should_create_card(pull_request_event):
        create_trello_card(pull_request_event)
        emit_dd_event(SUCCESS, "Succesfully created Trello card for PR {}".format(pr_url))
    else:
        print("Not creating a card for Pull Request {}".format(pr_url))
