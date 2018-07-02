# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from common import (PORT, SERVICE_CHECK, HOST)


def test_bad_config(check):
    """
    If misconfigured, the check should raise an Exception
    """
    with pytest.raises(Exception) as e:
        check.check({})
        # FIXME: the check should raise a more precise exception and there should be
        # no need to assert the content of the message!
        assert e.message == 'Either "url" or "socket" must be configured'


def test_service_ko(check, aggregator):
    """
    If the service is down, the service check should be sent accordingly
    """
    tags = ["host:{}".format(HOST), "port:{}".format(PORT), "foo:bar"]
    with pytest.raises(Exception) as e:
        check.check({'url': "{}".format(HOST), 'port': PORT, 'tags': ["foo:bar"]})
        # FIXME: the check should raise a more precise exception and there should be
        # no need to assert the content of the message!
        assert "Unable to retrieve stats from memcache instance" in e.message
    assert len(aggregator.service_checks(SERVICE_CHECK)) == 1
    sc = aggregator.service_checks(SERVICE_CHECK)[0]
    assert sc.status == check.CRITICAL
    assert sc.tags == tags
