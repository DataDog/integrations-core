# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from urllib.request import Request, urlopen


def is_leader(url: str) -> bool:
    request = Request(f'{url}/v3/maintenance/status', data=b'{}', method='POST')
    with urlopen(request, timeout=10) as result:
        response = json.loads(result.read())
    leader = response.get('leader')
    member = response.get('header', {}).get('member_id')

    return bool(leader and member and leader == member)
