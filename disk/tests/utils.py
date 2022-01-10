# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def assert_regex_equal(a, b):
    assert a.pattern == b.pattern
    assert a.flags == b.flags
