# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import mock
import pytest
import logging

from datadog_checks.openstack_controller.scopes import (Credential, Authenticator)
from datadog_checks.openstack_controller.exceptions import (IncompleteIdentity, MissingNovaEndpoint,
                                                            MissingNeutronEndpoint)

from . import common


log = logging.getLogger('test_openstack_controller')


def test_get_endpoint():
    authenticator = Authenticator()
    assert authenticator._get_nova_endpoint(
        common.EXAMPLE_AUTH_RESPONSE) == u'http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876'
    with pytest.raises(MissingNovaEndpoint):
        authenticator._get_nova_endpoint({})

    assert authenticator._get_neutron_endpoint(common.EXAMPLE_AUTH_RESPONSE) == u'http://10.0.2.15:9292'
    with pytest.raises(MissingNeutronEndpoint):
        authenticator._get_neutron_endpoint({})

    assert authenticator._get_valid_endpoint({}, None, None) is None
    assert authenticator._get_valid_endpoint({'token': {}}, None, None) is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": []}}, None, None) is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": []}}, None, None) is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{}]}}, None, None) is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{
        u'type': u'compute',
        u'name': u'nova'}]}}, None, None) is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [],
        u'type': u'compute',
        u'name': u'nova'}]}}, None, None) is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{u'url': u'dummy_url', u'interface': u'dummy'}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{u'url': u'dummy_url'}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{u'interface': u'public'}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{
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
    authenticator = Authenticator()
    with pytest.raises(IncompleteIdentity):
        authenticator._get_user_identity(user['user'])


def test_get_user_identity():
    authenticator = Authenticator()
    for user in BAD_USERS:
        _test_bad_user(user)

    for user in GOOD_USERS:
        parsed_user = authenticator._get_user_identity(user['user'])
        assert parsed_user == {'methods': ['password'], 'password': user}


class MockHTTPResponse(object):
    def __init__(self, response_dict, headers):
        self.response_dict = response_dict
        self.headers = headers

    def json(self):
        return self.response_dict


PROJECTS_RESPONSE = [
        {},
        {
            "domain_id": "0000",
        },
        {
            "domain_id": "1111",
            "id": "0000",
        },
        {
            "domain_id": "2222",
            "id": "1111",
            "name": "name 1"
        },
        {
            "domain_id": "3333",
            "id": "2222",
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


def test_from_config():
    mock_http_response = copy.deepcopy(common.EXAMPLE_AUTH_RESPONSE)
    mock_response = MockHTTPResponse(response_dict=mock_http_response, headers={'X-Subject-Token': 'fake_token'})

    with mock.patch('datadog_checks.openstack_controller.scopes.Authenticator._post_auth_token',
                    return_value=mock_response):
        with mock.patch('datadog_checks.openstack_controller.scopes.Authenticator._get_auth_projects',
                        return_value=PROJECTS_RESPONSE):
            cred = Authenticator.from_config(log, 'http://10.0.2.15:5000', GOOD_USERS[0]['user'])
            assert isinstance(cred, Credential)
            assert cred.auth_token == "fake_token"
            assert cred.project_auth_token == "fake_token"
            assert cred.name == "name 1"
            assert cred.domain_id == "2222"
            assert cred.tenant_id == "1111"
            assert cred.nova_endpoint == "http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876"
            assert cred.neutron_endpoint == "http://10.0.2.15:9292"


def test_from_config_with_missing_name():
    mock_http_response = copy.deepcopy(common.EXAMPLE_AUTH_RESPONSE)
    mock_response = MockHTTPResponse(response_dict=mock_http_response, headers={'X-Subject-Token': 'fake_token'})

    project_response_without_name = copy.deepcopy(PROJECT_RESPONSE)
    del project_response_without_name[0]["name"]

    with mock.patch('datadog_checks.openstack_controller.scopes.Authenticator._post_auth_token',
                    return_value=mock_response):
        with mock.patch('datadog_checks.openstack_controller.scopes.Authenticator._get_auth_projects',
                        return_value=project_response_without_name):
            cred = Authenticator.from_config(log, 'http://10.0.2.15:5000', GOOD_USERS[0]['user'])
            assert cred is None


def test_from_config_with_missing_id():
    mock_http_response = copy.deepcopy(common.EXAMPLE_AUTH_RESPONSE)
    mock_response = MockHTTPResponse(response_dict=mock_http_response, headers={'X-Subject-Token': 'fake_token'})

    project_response_without_name = copy.deepcopy(PROJECT_RESPONSE)
    del project_response_without_name[0]["id"]

    with mock.patch('datadog_checks.openstack_controller.scopes.Authenticator._post_auth_token',
                    return_value=mock_response):
        with mock.patch('datadog_checks.openstack_controller.scopes.Authenticator._get_auth_projects',
                        return_value=project_response_without_name):
            cred = Authenticator.from_config(log, 'http://10.0.2.15:5000', GOOD_USERS[0]['user'])
            assert cred is None
