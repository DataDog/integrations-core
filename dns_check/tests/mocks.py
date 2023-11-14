# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from dns.resolver import NXDOMAIN
from six import PY3


class MockDNSAnswer:
    def __init__(self, address):
        self.rrset = MockDNSAnswer.MockRrset(address)

    class MockRrset:
        def __init__(self, address):
            addresses = [x.strip().lower() for x in address.split(',')]
            if len(addresses) > 1:
                items = [MockDNSAnswer.MockItem(address) for address in addresses]
            else:
                items = [MockDNSAnswer.MockItem(address)]

            self.items = {item: None for item in items} if PY3 else items

    class MockItem:
        def __init__(self, address):
            self._address = address

        def to_text(self):
            return self._address


# We need to mock the calls to `time.time` on Windows,
# otherwise the consecutive calls are too close to one another in the check run with mocks,
# the time difference is `0` and no response_time metric is sent
class MockTime(object):
    global_time = 1

    @classmethod
    def time(cls):
        cls.global_time += 1
        return cls.global_time


def success_query_mock(d_name, rdtype):
    if rdtype == 'A':
        if d_name == 'my.example.org':
            return MockDNSAnswer('127.0.0.2,127.0.0.3,127.0.0.4')
        return MockDNSAnswer('127.0.0.2')
    elif rdtype == 'CNAME':
        return MockDNSAnswer('alias.example.org')


def nxdomain_query_mock(d_name):
    raise NXDOMAIN
