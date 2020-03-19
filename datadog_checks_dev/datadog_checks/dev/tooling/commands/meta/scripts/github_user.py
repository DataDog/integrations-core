# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click
import requests

from ...console import CONTEXT_SETTINGS, abort, echo_success


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Lookup Github username by email.')
@click.argument('email')
def github_user(email):
    """Given an email, attempt to find a Github username
       associated with the email.

    `$ ddev meta scripts github-user example@datadoghq.com`
    """
    usernames = []
    GITHUB_ENDPOINT = 'https://api.github.com/search/users'

    try:
        response = requests.get(f'{GITHUB_ENDPOINT}?q={email}',)
        response.raise_for_status()
        content = response.json()

        if content.get('total_count') == 0:
            abort(f'No username found for email {email}')

        for item in content.get('items'):
            username = item.get('login')
            usernames.append(username)

        usernames_formatted = ' \n'.join(usernames)

        echo_success(f'Username(s) associated with email {email}: \n{usernames_formatted}')

    except Exception as e:
        abort(str(e))
