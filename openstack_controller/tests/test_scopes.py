# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy

import mock
import pytest
from six import iteritems

from . import common

from datadog_checks.openstack_controller.exceptions import IncompleteIdentity
from datadog_checks.openstack_controller.scopes import (OpenStackProject, OpenStackScope)


def test_get_nova_endpoint():
    assert OpenStackScope._get_nova_endpoint(
        common.EXAMPLE_AUTH_RESPONSE) == u'http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876'
    assert OpenStackScope._get_nova_endpoint(
        common.EXAMPLE_AUTH_RESPONSE,
        nova_api_version='v2') == u'http://10.0.2.15:8773/'


def test_get_neutron_endpoint():
    assert OpenStackScope._get_neutron_endpoint(common.EXAMPLE_AUTH_RESPONSE) == u'http://10.0.2.15:9292'


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


MOCK_HTTP_RESPONSE = MockHTTPResponse(response_dict=common.EXAMPLE_AUTH_RESPONSE,
                                      headers={"X-Subject-Token": "fake_token"})
MOCK_HTTP_PROJECTS_RESPONSE = MockHTTPResponse(response_dict=common.EXAMPLE_PROJECTS_RESPONSE, headers={})

PROJECTS_RESPONSE = [
        {
            "domain_id": "1789d1",
            "enabled": True,
            "id": "263fd9",
            "links": {
                "self": "https://example.com/identity/v3/projects/263fd9"
            },
            "name": "Test Group"
        },
    ]


def test_unscoped_from_config():
    init_config = {'keystone_server_url': 'http://10.0.2.15:5000', 'nova_api_version': 'v2'}

    instance_config = {'user': GOOD_USERS[0]['user']}

    mock_http_response = copy.deepcopy(common.EXAMPLE_AUTH_RESPONSE)
    # mock_http_response['token'].pop('catalog')
    mock_http_response['token'].pop('project')
    mock_response = MockHTTPResponse(response_dict=mock_http_response, headers={'X-Subject-Token': 'fake_token'})
    with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.post_auth_token',
                    return_value=mock_response):
        with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.get_auth_projects',
                        return_value=PROJECTS_RESPONSE):
            instance_config['append_tenant_id'] = True
            scope = OpenStackScope.from_config(init_config, instance_config)
            assert isinstance(scope, OpenStackScope)

            assert scope.auth_token == 'fake_token'
            assert len(scope.project_scope_map) == 1
            for index, scope in iteritems(scope.project_scope_map):
                assert isinstance(scope, OpenStackProject)
                assert scope.auth_token == 'fake_token'
                assert scope.tenant_id == '263fd9'
