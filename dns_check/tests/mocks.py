# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from dns.resolver import NXDOMAIN


class MockDNSAnswer:
    def __init__(self, address):
        self.rrset = MockDNSAnswer.MockRrset(address)

    class MockRrset:
        def __init__(self, address):
            addresses = [x.strip().lower() for x in address.split(',')]
            if len(addresses) > 1:
                items = []
                for address in addresses:
                    items.append(MockDNSAnswer.MockItem(address))
                self.items = items
            else:
                self.items = [MockDNSAnswer.MockItem(address)]

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
