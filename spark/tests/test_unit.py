# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.spark import SparkCheck


@pytest.mark.parametrize(
    'base_url, relative_url, combined_url',
    [
        ('http://localhost:8080', '/metrics', "http://localhost:8080/metrics"),
        ('http://www.foo.com', '/bar/baz/buz', 'http://www.foo.com/bar/baz/buz'),
        ('https://www.foo2.com', '/bar2/baz2/buz2', 'https://www.foo2.com/bar2/baz2/buz2'),
    ],
)
def test_relative_link_transformer(instance, base_url, relative_url, combined_url):
    spark = SparkCheck('spark', {}, [instance])
    """
    Test to ensure that relative links are combined properly with a provided base url.
    """
    test_output = spark._relative_link_transformer(base_url, relative_url)
    assert str(test_output) == combined_url
