# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import mock
import pytest
import logging
from six import iteritems

from datadog_checks.openstack_controller.scopes import (Project, Scope, ScopeFetcher)
from datadog_checks.openstack_controller.exceptions import (IncompleteIdentity, MissingNovaEndpoint,
                                                            MissingNeutronEndpoint)

from . import common


log = logging.getLogger('test_openstack_controller')


def test_get_endpoint():
    scope_fetcher = ScopeFetcher()
    assert scope_fetcher._get_nova_endpoint(
        common.EXAMPLE_AUTH_RESPONSE) == u'http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876'
    with pytest.raises(MissingNovaEndpoint):
        scope_fetcher._get_nova_endpoint({})

    assert scope_fetcher._get_neutron_endpoint(common.EXAMPLE_AUTH_RESPONSE) == u'http://10.0.2.15:9292'
    with pytest.raises(MissingNeutronEndpoint):
        scope_fetcher._get_neutron_endpoint({})

    assert scope_fetcher._get_valid_endpoint({}, None, None) is None
    assert scope_fetcher._get_valid_endpoint({'token': {}}, None, None) is None
    assert scope_fetcher._get_valid_endpoint({'token': {"catalog": []}}, None, None) is None
    assert scope_fetcher._get_valid_endpoint({'token': {"catalog": []}}, None, None) is None
    assert scope_fetcher._get_valid_endpoint({'token': {"catalog": [{}]}}, None, None) is None
    assert scope_fetcher._get_valid_endpoint({'token': {"catalog": [{
        u'type': u'compute',
        u'name': u'nova'}]}}, None, None) is None
    assert scope_fetcher._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [],
        u'type': u'compute',
        u'name': u'nova'}]}}, None, None) is None
    assert scope_fetcher._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert scope_fetcher._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{u'url': u'dummy_url', u'interface': u'dummy'}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert scope_fetcher._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{u'url': u'dummy_url'}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert scope_fetcher._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{u'interface': u'public'}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert scope_fetcher._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{u'url': u'dummy_url', u'interface': u'internal'}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') == 'dummy_url'


BAD_USERS = [
    {'user': {}},
    {'user': {'name': ''}},
    {'user': {'name': 'test_name', 'password': ''}},
    {'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {}}},
    {'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': ''}}},
]

GOOD_USERS = [
    {'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}}},
]


def _test_bad_user(user):
    scope_fetcher = ScopeFetcher()
    with pytest.raises(IncompleteIdentity):
        scope_fetcher._get_user_identity(user)


def test_get_user_identity():
    scope_fetcher = ScopeFetcher()
    for user in BAD_USERS:
        _test_bad_user(user)

    for user in GOOD_USERS:
        parsed_user = scope_fetcher._get_user_identity(user)
        assert parsed_user == {'methods': ['password'], 'password': user}


class MockHTTPResponse(object):
    def __init__(self, response_dict, headers):
        self.response_dict = response_dict
        self.headers = headers

    def json(self):
        return self.response_dict


PROJECTS_RESPONSE = [
        {
            "domain_id": "1111",
            "id": "3333",
            "name": "name 1"
        },
        {
            "domain_id": "22222",
            "id": "4444",
            "name": "name 2"
        },
    ]

PROJECT_RESPONSE = [
        {
            "domain_id": "1111",
            "id": "3333",
            "name": "name 1"
        }
    ]


def test_from_config_simple(*args):
    init_config = {'keystone_server_url': 'http://10.0.2.15:5000'}
    instance_config = {'user': GOOD_USERS[0]['user']}

    mock_http_response = copy.deepcopy(common.EXAMPLE_AUTH_RESPONSE)
    mock_response = MockHTTPResponse(response_dict=mock_http_response, headers={'X-Subject-Token': 'fake_token'})

    with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.post_auth_token',
                    return_value=mock_response):
        with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.get_auth_projects',
                        return_value=PROJECTS_RESPONSE):
            scope = ScopeFetcher.from_config(log, init_config, instance_config)
            assert isinstance(scope, Scope)

            assert scope.auth_token == 'fake_token'
            assert len(scope.project_scopes) == 2
            expected_tenant_id = ['3333', '4444']
            for index, scope in iteritems(scope.project_scopes):
                assert isinstance(scope, Project)
                assert scope.auth_token == 'fake_token'
                assert scope.tenant_id in expected_tenant_id
                expected_tenant_id.remove(scope.tenant_id)


def test_from_config_with_missing_name(*args):
    init_config = {'keystone_server_url': 'http://10.0.2.15:5000'}

    instance_config = {'user': GOOD_USERS[0]['user']}

    mock_http_response = copy.deepcopy(common.EXAMPLE_AUTH_RESPONSE)
    mock_response = MockHTTPResponse(response_dict=mock_http_response, headers={'X-Subject-Token': 'fake_token'})

    project_response_without_name = copy.deepcopy(PROJECTS_RESPONSE)
    del project_response_without_name[0]["name"]

    with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.post_auth_token',
                    return_value=mock_response):
        with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.get_auth_projects',
                        return_value=project_response_without_name):
            scope = ScopeFetcher.from_config(log, init_config, instance_config, proxy_config=None)
            assert len(scope.project_scopes) == 0


def test_from_config_with_missing_id(*args):
    init_config = {'keystone_server_url': 'http://10.0.2.15:5000'}

    instance_config = {'user': GOOD_USERS[0]['user']}

    mock_http_response = copy.deepcopy(common.EXAMPLE_AUTH_RESPONSE)
    mock_response = MockHTTPResponse(response_dict=mock_http_response, headers={'X-Subject-Token': 'fake_token'})

    project_response_without_name = copy.deepcopy(PROJECTS_RESPONSE)
    del project_response_without_name[0]["id"]

    with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.post_auth_token',
                    return_value=mock_response):
        with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.get_auth_projects',
                        return_value=project_response_without_name):
            scope = ScopeFetcher.from_config(log, init_config, instance_config, proxy_config=None)
            assert len(scope.project_scopes) == 0
