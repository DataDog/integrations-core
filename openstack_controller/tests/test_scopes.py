# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy

import mock
import pytest
from six import iteritems

from . import common

from datadog_checks.openstack_controller.exceptions import (IncompleteIdentity, MissingNovaEndpoint,
                                                            MissingNeutronEndpoint)
from datadog_checks.openstack_controller.scopes import (OpenStackProject, OpenStackScope)


def test_get_endpoint():
    assert OpenStackScope._get_nova_endpoint(
        common.EXAMPLE_AUTH_RESPONSE) == u'http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876'
    with pytest.raises(MissingNovaEndpoint):
        OpenStackScope._get_nova_endpoint({})

    assert OpenStackScope._get_neutron_endpoint(common.EXAMPLE_AUTH_RESPONSE) == u'http://10.0.2.15:9292'
    with pytest.raises(MissingNeutronEndpoint):
        OpenStackScope._get_neutron_endpoint({})

    assert OpenStackScope._get_valid_endpoint({}, None, None) is None
    assert OpenStackScope._get_valid_endpoint({'token': {}}, None, None) is None
    assert OpenStackScope._get_valid_endpoint({'token': {"catalog": []}}, None, None) is None
    assert OpenStackScope._get_valid_endpoint({'token': {"catalog": []}}, None, None) is None
    assert OpenStackScope._get_valid_endpoint({'token': {"catalog": [{}]}}, None, None) is None
    assert OpenStackScope._get_valid_endpoint({'token': {"catalog": [{
        u'type': u'compute',
        u'name': u'nova'}]}}, None, None) is None
    assert OpenStackScope._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [],
        u'type': u'compute',
        u'name': u'nova'}]}}, None, None) is None
    assert OpenStackScope._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert OpenStackScope._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{u'url': u'dummy_url', u'interface': u'dummy'}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert OpenStackScope._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{u'url': u'dummy_url'}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert OpenStackScope._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{u'interface': u'public'}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert OpenStackScope._get_valid_endpoint({'token': {"catalog": [{
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
    with pytest.raises(IncompleteIdentity):
        OpenStackScope._get_user_identity(user)


def test_get_user_identity():
    for user in BAD_USERS:
        _test_bad_user(user)

    for user in GOOD_USERS:
        parsed_user = OpenStackScope._get_user_identity(user)
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


def test_from_config_simple():
    init_config = {'keystone_server_url': 'http://10.0.2.15:5000', 'nova_api_version': 'v2'}

    instance_config = {'user': GOOD_USERS[0]['user']}

    mock_http_response = copy.deepcopy(common.EXAMPLE_AUTH_RESPONSE)
    mock_response = MockHTTPResponse(response_dict=mock_http_response, headers={'X-Subject-Token': 'fake_token'})

    with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.post_auth_token',
                    return_value=mock_response):
        with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.get_auth_projects',
                        return_value=PROJECTS_RESPONSE):
            scope = OpenStackScope.from_config(init_config, instance_config)
            assert isinstance(scope, OpenStackScope)

            assert scope.auth_token == 'fake_token'
            assert len(scope.project_scope_map) == 2
            expected_tenant_id = ['3333', '4444']
            for index, scope in iteritems(scope.project_scope_map):
                assert isinstance(scope, OpenStackProject)
                assert scope.auth_token == 'fake_token'
                assert scope.tenant_id in expected_tenant_id
                expected_tenant_id.remove(scope.tenant_id)


def test_from_config_with_missing_name():
    init_config = {'keystone_server_url': 'http://10.0.2.15:5000', 'nova_api_version': 'v2'}

    instance_config = {'user': GOOD_USERS[0]['user']}

    mock_http_response = copy.deepcopy(common.EXAMPLE_AUTH_RESPONSE)
    mock_response = MockHTTPResponse(response_dict=mock_http_response, headers={'X-Subject-Token': 'fake_token'})

    project_response_without_name = copy.deepcopy(PROJECTS_RESPONSE)
    del project_response_without_name[0]["name"]

    with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.post_auth_token',
                    return_value=mock_response):
        with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.get_auth_projects',
                        return_value=project_response_without_name):
            scope = OpenStackScope.from_config(init_config, instance_config)
            assert len(scope.project_scope_map) == 0


def test_from_config_with_missing_id():
    init_config = {'keystone_server_url': 'http://10.0.2.15:5000', 'nova_api_version': 'v2'}

    instance_config = {'user': GOOD_USERS[0]['user']}

    mock_http_response = copy.deepcopy(common.EXAMPLE_AUTH_RESPONSE)
    mock_response = MockHTTPResponse(response_dict=mock_http_response, headers={'X-Subject-Token': 'fake_token'})

    project_response_without_name = copy.deepcopy(PROJECTS_RESPONSE)
    del project_response_without_name[0]["id"]

    with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.post_auth_token',
                    return_value=mock_response):
        with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.get_auth_projects',
                        return_value=project_response_without_name):
            scope = OpenStackScope.from_config(init_config, instance_config)
            assert len(scope.project_scope_map) == 0
