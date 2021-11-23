# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import requests

from .common import V3_PREVIEW

legacy = pytest.mark.skipif(V3_PREVIEW, reason='Requires < v3')
preview = pytest.mark.skipif(not V3_PREVIEW, reason='Requires >= v3')


def is_leader(url):
    if V3_PREVIEW:
        response = requests.post('{}/v3beta/maintenance/status'.format(url), data='{}').json()
        leader = response.get('leader')
        member = response.get('header', {}).get('member_id')

        return leader and member and leader == member
    else:
        response = requests.get('{}/v2/stats/self'.format(url))

        return response.json().get('state') == 'StateLeader'
