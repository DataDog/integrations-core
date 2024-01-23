# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json  # noqa: F401
import os
import sys
import time

import datadog as dd
import requests

GITHUB_ISSUES_API = 'https://api.github.com/search/issues?q=sha:{}+repo:DataDog/{}'
TRELLO_CARDS_API = 'https://api.trello.com/1/cards'
TRELLO_LIST_ID = '5c8fd508f129f77d19b50de4'
TAGS = ['team:agent-integrations', 'application:release_reminder']

REPO = 'integrations-core'
DD_API_KEY = None
TRELLO_KEY = None
TRELLO_TOKEN = None

def main():
    global DD_API_KEY, REPO, TRELLO_KEY, TRELLO_TOKEN

    if len(sys.argv) > 1:
        REPO = sys.argv[1]

    try:
        DD_API_KEY = os.environ['DD_API_KEY']
        TRELLO_KEY = os.environ['TRELLO_KEY']
        TRELLO_TOKEN = os.environ['TRELLO_TOKEN']
    except KeyError as e:
        env_var = str(e).replace('KeyError:', '', 1).strip(' "\'')
        raise EnvironmentError(f'Missing required environment variable `{env_var}`')

    dd.initialize(api_key=DD_API_KEY)

    pull_request = get_latest_pr()

    if should_create_card(pull_request):
        create_trello_card(pull_request)
    else:
        pr_url = pull_request.get('html_url')
        print(f'Not creating a card for Pull Request {pr_url}')


def exit_success(message):
    title = 'SUCCESS: Trello card creation'

    emit_dd_event(title, message)

    print(message)
    sys.exit(0)


def exit_failure(message):
    title = 'FAILURE: Trello card creation'

    try:
        emit_dd_event(title, message)
    except Exception:
        pass

    sys.exit(message)


# Emit an event to Datadog based on whether or not we could create the card
def emit_dd_event(title, message):
    dd.api.Event.create(title=title, text=message, tags=TAGS)


# Create the Trello card on the list specified by TRELLO_LIST_ID
# https://developers.trello.com/reference/#cards-2
def create_trello_card(pull_request):
    pr_url = pull_request.get('html_url', 'Unknown')
    pr_body = pull_request.get('body', '')
    description = f'Pull request: {pr_url}\n\n{pr_body}'

    params = {
        'key': TRELLO_KEY,
        'token': TRELLO_TOKEN,
        'idList': TRELLO_LIST_ID,
        'keepFromSource': 'all',
        'name': pull_request.get('title', 'Release reminder'),
        # It appears the character limit for descriptions is ~5000
        'desc': description[:5000],
    }

    creation_attempts = 3
    for attempt in range(3):
        rate_limited, error, response = handle_trello_api(params)

        if rate_limited:
            wait_time = 10
            print(
                f'Attempt {attempt + 1} of {creation_attempts}: '
                f'A rate limit in effect, retrying in {wait_time} seconds...'
            )
            time.sleep(wait_time)
        elif error:
            if attempt + 1 == creation_attempts:
                exit_failure(error.replace(TRELLO_KEY, 'redacted').replace(TRELLO_TOKEN, 'redacted'))

            wait_time = 2
            print(
                f'Attempt {attempt + 1} of {creation_attempts}: '
                f'An error has occurred, retrying in {wait_time} seconds...'
            )
            time.sleep(wait_time)
        else:
            card_url = response.json().get('url')
            exit_success(f'Created card: {card_url}')
    else:
        exit_failure('Too many card creation attempts')


def handle_trello_api(params):
    rate_limited = False
    error = ''
    response = None

    try:
        response = requests.post(TRELLO_CARDS_API, params=params)
    except Exception as e:
        error = str(e)
    else:
        try:
            response.raise_for_status()
        except Exception as e:
            error = str(e)

    # Rate limit
    if response:
        rate_limited = response.status_code == 429

    return rate_limited, error, response


def get_latest_pr():
    commit_hash = os.environ['CI_COMMIT_SHA']
    url = GITHUB_ISSUES_API.format(commit_hash, REPO)

    creation_attempts = 3
    for attempt in range(3):
        rate_limited, error, response = handle_github_api(url)

        if rate_limited:
            wait_time = 10
            print(
                f'Attempt {attempt + 1} of {creation_attempts}: '
                f'A rate limit in effect, retrying in {wait_time} seconds...'
            )
            time.sleep(wait_time)
        elif error:
            if attempt + 1 == creation_attempts:
                exit_failure(error)

            wait_time = 2
            print(
                f'Attempt {attempt + 1} of {creation_attempts}: '
                f'An error has occurred, retrying in {wait_time} seconds...'
            )
            time.sleep(wait_time)
        else:
            pr_data = response.json()
            try:
                pr_data = pr_data.get('items', [{}])[0]
            # Commit to master
            except IndexError:
                pr_data = {'html_url': 'https://github.com/DataDog/{}/commit/{}'.format(REPO, commit_hash)}
            return pr_data
    else:
        exit_failure(f'Too many retries for: {url}')


def handle_github_api(url):
    rate_limited = False
    error = None
    response = None

    try:
        response = requests.get(url)
    except Exception as e:
        error = str(e)
    else:
        try:
            response.raise_for_status()
        except Exception as e:
            error = str(e)

    # Rate limit
    if response:
        rate_limited = response.status_code == 403

    return rate_limited, error, response


# Use the github labels from the PR to determine if we should create a Trello card
# Return true if any of the labels on the PR starts with changelog and isn't `no-changelog`
def should_create_card(pull_request):
    for label in pull_request.get('labels', []):
        label = label.get('name', '')
        if label.startswith('changelog/') and label != 'changelog/no-changelog':
            return True

    return False


if __name__ == '__main__':
    main()
