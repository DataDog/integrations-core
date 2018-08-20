# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests


def is_leader(url):
    response = requests.get('{}/v2/stats/self'.format(url))

    return response.json().get('state') == 'StateLeader'
