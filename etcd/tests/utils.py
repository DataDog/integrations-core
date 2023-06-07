# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import requests

V3_PREVIEW = True

legacy = pytest.mark.skipif(V3_PREVIEW, reason='Requires < v3')
preview = pytest.mark.skipif(not V3_PREVIEW, reason='Requires >= v3')


def is_leader(url):
    response = requests.post('{}/v3beta/maintenance/status'.format(url), data='{}').json()
    leader = response.get('leader')
    member = response.get('header', {}).get('member_id')

    return leader and member and leader == member
