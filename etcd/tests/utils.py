# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import urllib.error
import urllib.request


def is_leader(url):
    req = urllib.request.Request('{}/v3/maintenance/status'.format(url), data=b'{}', method='POST')
    try:
        resp = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        resp = e
    try:
        response = json.load(resp)
    finally:
        resp.close()
    leader = response.get('leader')
    member = response.get('header', {}).get('member_id')

    return leader and member and leader == member
