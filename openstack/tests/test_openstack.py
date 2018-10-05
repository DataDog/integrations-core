# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import copy
import re
import time

# 3p
import mock
import pytest

# project
import common

from datadog_checks.openstack.openstack import (
    OpenStackCheck,
    OpenStackProjectScope,
    OpenStackUnscoped,
    KeystoneCatalog,
    IncompleteConfig,
    IncompleteAuthScope,
    IncompleteIdentity
)

from datadog_checks.checks import AgentCheck

instance = common.MOCK_CONFIG["instances"][0]
instance['tags'] = ['optional:tag1']
init_config = common.MOCK_CONFIG['init_config']
openstack_check = OpenStackCheck('openstack', init_config, {}, instances=[instance])


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


class MockHTTPResponse(object):
    def __init__(self, response_dict, headers):
        self.response_dict = response_dict
        self.headers = headers

    def json(self):
        return self.response_dict


MOCK_HTTP_RESPONSE = MockHTTPResponse(
    response_dict=common.EXAMPLE_AUTH_RESPONSE, headers={
        "X-Subject-Token": "fake_token"})
MOCK_HTTP_PROJECTS_RESPONSE = MockHTTPResponse(response_dict=common.EXAMPLE_PROJECTS_RESPONSE, headers={})


def _test_bad_auth_scope(scope):
    with pytest.raises(IncompleteAuthScope):
        OpenStackProjectScope.get_auth_scope(scope)


def _test_bad_user(user):
    with pytest.raises(IncompleteIdentity):
        OpenStackProjectScope.get_user_identity(user)


def test_get_auth_scope():
    for scope in common.BAD_AUTH_SCOPES:
        _test_bad_auth_scope(scope)

    for scope in common.GOOD_UNSCOPED_AUTH_SCOPES:
        auth_scope = OpenStackProjectScope.get_auth_scope(scope)
        assert auth_scope is None
        auth_scope = OpenStackUnscoped.get_auth_scope(scope)

        assert auth_scope is None

    for scope in common.GOOD_AUTH_SCOPES:
        auth_scope = OpenStackProjectScope.get_auth_scope(scope)

        # Should pass through unchanged
        assert auth_scope == scope.get('auth_scope')


def test_get_user_identity():
    for user in common.BAD_USERS:
        _test_bad_user(user)

    for user in common.GOOD_USERS:
        parsed_user = OpenStackProjectScope.get_user_identity(user)
        assert parsed_user == {'methods': ['password'], 'password': user}


def test_from_config():
    init_config = {'keystone_server_url': 'http://10.0.2.15:5000', 'nova_api_version': 'v2'}
    bad_instance_config = {}

    good_instance_config = {'user': common.GOOD_USERS[0]['user'],
                            'auth_scope': common.GOOD_AUTH_SCOPES[0]['auth_scope']}

    with pytest.raises(IncompleteConfig):
        OpenStackProjectScope.from_config(init_config, bad_instance_config)

    with mock.patch(
        'datadog_checks.openstack.openstack.OpenStackProjectScope.request_auth_token',
        return_value=MOCK_HTTP_RESPONSE
    ):
        append_config = good_instance_config.copy()
        append_config['append_tenant_id'] = True
        scope = OpenStackProjectScope.from_config(init_config, append_config)
        assert isinstance(scope, OpenStackProjectScope)

        assert scope.auth_token == 'fake_token'
        assert scope.tenant_id == 'test_project_id'

        # Test that append flag worked
        assert scope.service_catalog.nova_endpoint == 'http://10.0.2.15:8773/test_project_id'


def test_unscoped_from_config():
    init_config = {'keystone_server_url': 'http://10.0.2.15:5000', 'nova_api_version': 'v2'}

    good_instance_config = {'user': common.GOOD_USERS[0]['user'],
                            'auth_scope': common.GOOD_UNSCOPED_AUTH_SCOPES[0]['auth_scope']}

    mock_http_response = copy.deepcopy(common.EXAMPLE_AUTH_RESPONSE)
    mock_http_response['token'].pop('catalog')
    mock_http_response['token'].pop('project')
    mock_response = MockHTTPResponse(response_dict=mock_http_response, headers={'X-Subject-Token': 'fake_token'})
    with mock.patch(
        'datadog_checks.openstack.openstack.OpenStackUnscoped.request_auth_token',
        return_value=mock_response
    ):
        with mock.patch(
            'datadog_checks.openstack.openstack.OpenStackUnscoped.request_project_list',
            return_value=MOCK_HTTP_PROJECTS_RESPONSE
        ):
            with mock.patch(
                'datadog_checks.openstack.openstack.OpenStackUnscoped.get_token_for_project',
                return_value=MOCK_HTTP_RESPONSE
            ):
                append_config = good_instance_config.copy()
                append_config['append_tenant_id'] = True
                scope = OpenStackUnscoped.from_config(init_config, append_config)
                assert isinstance(scope, OpenStackUnscoped)

                assert scope.auth_token == 'fake_token'
                assert len(scope.project_scope_map) == 1
                for _, scope in scope.project_scope_map.iteritems():
                    assert isinstance(scope, OpenStackProjectScope)
                    assert scope.auth_token == 'fake_token'
                    assert scope.tenant_id == '263fd9'


def test_get_nova_endpoint():
    assert KeystoneCatalog.get_nova_endpoint(
        common.EXAMPLE_AUTH_RESPONSE) == u'http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876'
    assert KeystoneCatalog.get_nova_endpoint(
        common.EXAMPLE_AUTH_RESPONSE,
        nova_api_version='v2') == u'http://10.0.2.15:8773/'


def test_get_neutron_endpoint():
    assert KeystoneCatalog.get_neutron_endpoint(common.EXAMPLE_AUTH_RESPONSE) == u'http://10.0.2.15:9292'


def test_from_auth_response():
    catalog = KeystoneCatalog.from_auth_response(common.EXAMPLE_AUTH_RESPONSE, 'v2.1')
    assert isinstance(catalog, KeystoneCatalog)
    assert catalog.neutron_endpoint == u'http://10.0.2.15:9292'
    assert catalog.nova_endpoint == u'http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876'


def test_ensure_auth_scope(aggregator):
    instance = common.MOCK_CONFIG["instances"][0]
    instance['tags'] = ['optional:tag1']

    with pytest.raises(KeyError):
        openstack_check.get_scope_for_instance(instance)

    with mock.patch(
        'datadog_checks.openstack.openstack.OpenStackProjectScope.request_auth_token',
        return_value=MOCK_HTTP_RESPONSE
    ):
        scope = openstack_check.ensure_auth_scope(instance)

        assert openstack_check.get_scope_for_instance(instance) == scope
        openstack_check._send_api_service_checks(scope, ['optional:tag1'])
        aggregator.assert_service_check(
            OpenStackCheck.IDENTITY_API_SC, status=AgentCheck.OK, tags=[
                'optional:tag1', 'keystone_server:http://10.0.2.15:5000'])

        # URLs are nonexistant, so return CRITICAL
        aggregator.assert_service_check(OpenStackCheck.COMPUTE_API_SC, status=AgentCheck.CRITICAL)
        aggregator.assert_service_check(OpenStackCheck.NETWORK_API_SC, status=AgentCheck.CRITICAL)

        openstack_check._current_scope = scope

    openstack_check.delete_current_scope()

    with pytest.raises(KeyError):
        openstack_check.get_scope_for_instance(instance)


def test_parse_uptime_string():
    uptime_parsed = openstack_check._parse_uptime_string(
        u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n')
    assert uptime_parsed.get('loads') == [0.04, 0.14, 0.19]


def test_cache_utils():
    openstack_check.CACHE_TTL['aggregates'] = 1
    expected_aggregates = {'hyp_1': ['aggregate:staging', 'availability_zone:test']}

    with mock.patch(
        'datadog_checks.openstack.OpenStackCheck.get_all_aggregate_hypervisors',
        return_value=expected_aggregates
    ):
        assert openstack_check._get_and_set_aggregate_list() == expected_aggregates
        time.sleep(1.5)
        assert openstack_check._is_expired('aggregates')


@mock.patch('datadog_checks.openstack.OpenStackCheck.get_all_servers', return_value=common.ALL_SERVER_DETAILS)
def test_server_exclusion(*args):
    """
    Exclude servers using regular expressions.
    """
    openstackCheck = OpenStackCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS
    }, {}, instances=common.MOCK_CONFIG)

    # Retrieve servers
    openstackCheck.server_details_by_id = copy.deepcopy(common.ALL_SERVER_DETAILS)
    openstackCheck.filter_excluded_servers()
    server_ids = openstackCheck.server_details_by_id
    # Assert
    # .. 1 out of 4 server ids filtered
    assert len(server_ids) == 1

    # Ensure the server IDs filtered are the ones expected
    for server_id in server_ids:
        assert server_id in common.FILTERED_SERVER_ID


@mock.patch('datadog_checks.openstack.OpenStackCheck.get_all_servers', return_value=common.ALL_SERVER_DETAILS)
def test_server_exclusion_by_project(*args):
    """
    Exclude servers using regular expressions.
    """
    openstackCheck = OpenStackCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'blacklist_project_names': ["blacklist*"]
    }, {}, instances=common.MOCK_CONFIG)

    # Retrieve servers
    openstackCheck.server_details_by_id = copy.deepcopy(common.ALL_SERVER_DETAILS)
    openstackCheck.filter_excluded_servers()
    server_ids = openstackCheck.server_details_by_id
    # Assert
    # .. 2 out of 4 server ids filtered
    assert len(server_ids) == 2

    # Ensure the server IDs filtered are the ones expected
    for server_id in server_ids:
        assert server_id in common.FILTERED_BY_PROJ_SERVER_ID


@mock.patch('datadog_checks.openstack.OpenStackCheck.get_all_servers', return_value=common.ALL_SERVER_DETAILS)
def test_server_include_all_by_default(*args):
    """
    Exclude servers using regular expressions.
    """
    openstackCheck = OpenStackCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False
    }, {}, instances=common.MOCK_CONFIG)

    # Retrieve servers
    openstackCheck.server_details_by_id = copy.deepcopy(common.ALL_SERVER_DETAILS)
    openstackCheck.filter_excluded_servers()
    server_ids = openstackCheck.server_details_by_id
    # Assert
    # All 4 servers should still be monitored
    assert len(server_ids) == 4


@mock.patch('datadog_checks.openstack.OpenStackCheck.get_all_network_ids', return_value=common.ALL_IDS)
def test_network_exclusion(*args):
    """
    Exclude networks using regular expressions.
    """
    with mock.patch('datadog_checks.openstack.OpenStackCheck.get_stats_for_single_network') \
            as mock_get_stats_single_network:

        openstack_check.exclude_network_id_rules = set([re.compile(rule) for rule in common.EXCLUDED_NETWORK_IDS])

        # Retrieve network stats
        openstack_check.get_network_stats([])

        # Assert
        # .. 1 out of 4 network filtered in
        assert mock_get_stats_single_network.call_count == 1
        assert mock_get_stats_single_network.call_args[0][0] == common.FILTERED_NETWORK_ID

        # cleanup
        openstack_check.exclude_network_id_rules = set([])


@mock.patch(
    'datadog_checks.openstack.OpenStackCheck._make_request_with_auth_fallback',
    return_value=common.MOCK_NOVA_SERVERS)
@mock.patch('datadog_checks.openstack.OpenStackCheck.get_nova_endpoint',
            return_value="http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876")
@mock.patch('datadog_checks.openstack.OpenStackCheck.get_auth_token', return_value="test_auth_token")
@mock.patch('datadog_checks.openstack.OpenStackCheck.get_project_name_from_id', return_value="tenant-1")
def test_cache_between_runs(self, *args):
    """
    Ensure the cache contains the expected VMs between check runs.
    """

    openstackCheck = OpenStackCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS
    }, {}, instances=common.MOCK_CONFIG)

    # Start off with a list of servers
    openstackCheck.server_details_by_id = copy.deepcopy(common.ALL_SERVER_DETAILS)
    i_key = "test_instance"

    # Update the cached list of servers based on what the endpoint returns
    openstackCheck.get_all_servers(i_key)

    cached_servers = openstackCheck.server_details_by_id
    assert 'server-1' not in cached_servers
    assert 'server_newly_added' in cached_servers


@mock.patch(
    'datadog_checks.openstack.OpenStackCheck._make_request_with_auth_fallback',
    return_value=common.MOCK_NOVA_SERVERS)
@mock.patch('datadog_checks.openstack.OpenStackCheck.get_nova_endpoint',
            return_value="http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876")
@mock.patch('datadog_checks.openstack.OpenStackCheck.get_auth_token', return_value="test_auth_token")
@mock.patch('datadog_checks.openstack.OpenStackCheck.get_project_name_from_id', return_value="None")
def test_project_name_none(self, *args):
    """
    Ensure the cache contains the expected VMs between check runs.
    """

    openstackCheck = OpenStackCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS
    }, {}, instances=common.MOCK_CONFIG)

    # Start off with a list of servers
    openstackCheck.server_details_by_id = copy.deepcopy(common.ALL_SERVER_DETAILS)
    i_key = "test_instance"

    # Update the cached list of servers based on what the endpoint returns
    openstackCheck.get_all_servers(i_key)
    assert len(self.server_details_by_id) == 0
