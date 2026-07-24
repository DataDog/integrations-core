# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.http import http_post


def is_leader(url):
    response = http_post('{}/v3/maintenance/status'.format(url), data='{}').json()
    leader = response.get('leader')
    member = response.get('header', {}).get('member_id')

    return leader and member and leader == member
