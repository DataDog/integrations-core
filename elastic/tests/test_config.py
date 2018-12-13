# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.elastic.config import from_instance, DEFAULT_TIMEOUT


@pytest.mark.unit
def test_from_instance_invalid():
    # missing url
    with pytest.raises(ConfigurationError):
        from_instance({})
    # empty url
    with pytest.raises(ConfigurationError):
        from_instance({'url': ''})


@pytest.mark.unit
def test_from_instance_defaults():
    c = from_instance({'url': 'http://example.com'})

    assert c.admin_forwarder is False
    assert c.pshard_stats is False
    assert c.pshard_graceful_to is False
    assert c.cluster_stats is False
    assert c.index_stats is False
    assert c.password is None
    assert c.service_check_tags == ['host:example.com', 'port:None']
    assert c.health_tags == []
    assert c.ssl_cert is None
    assert c.ssl_key is None
    assert c.ssl_verify is None
    assert c.tags == ['url:http://example.com']
    assert c.timeout == DEFAULT_TIMEOUT
    assert c.url == 'http://example.com'
    assert c.username is None
    assert c.pending_task_stats is True


@pytest.mark.unit
def test_from_instance_cluster_stats():
    c = from_instance({'url': 'http://example.com', 'is_external': True})
    assert c.cluster_stats is True


@pytest.mark.unit
def test_from_instance():
    instance = {
        "username": "user",
        "password": "pass",
        "is_external": "yes",
        "url": "http://foo.bar",
        "tags": ["a", "b:c"],
    }
    c = from_instance(instance)
    assert c.username == "user"
    assert c.password == "pass"
    assert c.admin_forwarder is False
    assert c.cluster_stats is True
    assert c.url == "http://foo.bar"
    assert c.tags == ["url:http://foo.bar", "a", "b:c"]
    assert c.timeout == DEFAULT_TIMEOUT
    assert c.service_check_tags == ["host:foo.bar", "port:None", "a", "b:c"]

    instance = {"url": "http://192.168.42.42:12999", "timeout": 15}
    c = from_instance(instance)
    assert c.username is None
    assert c.password is None
    assert c.cluster_stats is False
    assert c.url == "http://192.168.42.42:12999"
    assert c.tags == ["url:http://192.168.42.42:12999"]
    assert c.timeout == 15
    assert c.service_check_tags == ["host:192.168.42.42", "port:12999"]

    instance = {
        "username": "user",
        "password": "pass",
        "url": "https://foo.bar:9200",
        "ssl_verify": "true",
        "ssl_cert": "/path/to/cert.pem",
        "ssl_key": "/path/to/cert.key",
        "admin_forwarder": "1",
    }
    c = from_instance(instance)
    assert c.username == "user"
    assert c.password == "pass"
    assert c.admin_forwarder is True
    assert c.cluster_stats is False
    assert c.url == "https://foo.bar:9200"
    assert c.tags == ["url:https://foo.bar:9200"]
    assert c.timeout == DEFAULT_TIMEOUT
    assert c.service_check_tags == ["host:foo.bar", "port:9200"]
    assert c.ssl_verify == "true"
    assert c.ssl_cert == "/path/to/cert.pem"
    assert c.ssl_key == "/path/to/cert.key"
