# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datetime import datetime, timedelta
from six.moves.urllib.parse import urljoin
import re
import time
import random
import copy

import requests
import simplejson as json
from six import iteritems

from datadog_checks.checks import AgentCheck
from datadog_checks.config import is_affirmative
from datadog_checks.utils.common import pattern_filter

try:
    # Agent >= 6.0: the check pushes tags invoking `set_external_tags`
    from datadog_agent import set_external_tags
except ImportError:
    # Agent < 6.0: the Agent pulls tags invoking `OpenStackControllerCheck.get_external_host_tags`
    set_external_tags = None


SOURCE_TYPE = 'openstack'

V21_NOVA_API_VERSION = 'v2.1'

DEFAULT_KEYSTONE_API_VERSION = 'v3'
DEFAULT_NOVA_API_VERSION = V21_NOVA_API_VERSION
FALLBACK_NOVA_API_VERSION = 'v2'
DEFAULT_NEUTRON_API_VERSION = 'v2.0'

DEFAULT_PAGINATED_SERVER_LIMIT = 1000

DEFAULT_API_REQUEST_TIMEOUT = 10  # seconds

NOVA_HYPERVISOR_METRICS = [
    'current_workload',
    'disk_available_least',
    'free_disk_gb',
    'free_ram_mb',
    'local_gb',
    'local_gb_used',
    'memory_mb',
    'memory_mb_used',
    'running_vms',
    'vcpus',
    'vcpus_used',
]

NOVA_SERVER_METRICS = [
    "hdd_errors",
    "hdd_read",
    "hdd_read_req",
    "hdd_write",
    "hdd_write_req",
    "memory",
    "memory-actual",
    "memory-rss",
    "cpu0_time",
    "vda_errors",
    "vda_read",
    "vda_read_req",
    "vda_write",
    "vda_write_req",
]

NOVA_SERVER_INTERFACE_SEGMENTS = ['_rx', '_tx']

PROJECT_METRICS = dict(
    [
        ("maxImageMeta", "max_image_meta"),
        ("maxPersonality", "max_personality"),
        ("maxPersonalitySize", "max_personality_size"),
        ("maxSecurityGroupRules", "max_security_group_rules"),
        ("maxSecurityGroups", "max_security_groups"),
        ("maxServerMeta", "max_server_meta"),
        ("maxTotalCores", "max_total_cores"),
        ("maxTotalFloatingIps", "max_total_floating_ips"),
        ("maxTotalInstances", "max_total_instances"),
        ("maxTotalKeypairs", "max_total_keypairs"),
        ("maxTotalRAMSize", "max_total_ram_size"),
        ("totalImageMetaUsed", "total_image_meta_used"),
        ("totalPersonalityUsed", "total_personality_used"),
        ("totalPersonalitySizeUsed", "total_personality_size_used"),
        ("totalSecurityGroupRulesUsed", "total_security_group_rules_used"),
        ("totalSecurityGroupsUsed", "total_security_groups_used"),
        ("totalServerMetaUsed", "total_server_meta_used"),
        ("totalCoresUsed", "total_cores_used"),
        ("totalFloatingIpsUsed", "total_floating_ips_used"),
        ("totalInstancesUsed", "total_instances_used"),
        ("totalKeypairsUsed", "total_keypairs_used"),
        ("totalRAMUsed", "total_ram_used"),
    ]
)

DIAGNOSTICABLE_STATES = ['ACTIVE']

REMOVED_STATES = ['DELETED', 'SHUTOFF']

UNSCOPED_AUTH = 'unscoped'

BASE_BACKOFF_SECS = 15
MAX_BACKOFF_SECS = 300

SERVER_FIELDS_REQ = [
    'server_id',
    'state',
    'server_name',
    'hypervisor_hostname',
    'tenant_id',
]


class OpenStackAuthFailure(Exception):
    pass


class InstancePowerOffFailure(Exception):
    pass


class IncompleteConfig(Exception):
    pass


class IncompleteAuthScope(IncompleteConfig):
    pass


class IncompleteIdentity(IncompleteConfig):
    pass


class MissingEndpoint(Exception):
    pass


class MissingNovaEndpoint(MissingEndpoint):
    pass


class MissingNeutronEndpoint(MissingEndpoint):
    pass


class KeystoneUnreachable(Exception):
    pass


class OpenStackScope(object):
    def __init__(self, auth_token):
        self.auth_token = auth_token

    @classmethod
    def request_auth_token(cls, auth_scope, identity, keystone_server_url, ssl_verify, proxy=None):
        if not auth_scope:
            auth_scope = UNSCOPED_AUTH

        payload = {'auth': {'identity': identity, 'scope': auth_scope}}
        auth_url = urljoin(keystone_server_url, "{}/auth/tokens".format(DEFAULT_KEYSTONE_API_VERSION))
        headers = {'Content-Type': 'application/json'}

        resp = requests.post(
            auth_url,
            headers=headers,
            data=json.dumps(payload),
            verify=ssl_verify,
            timeout=DEFAULT_API_REQUEST_TIMEOUT,
            proxies=proxy,
        )
        resp.raise_for_status()

        return resp

    @classmethod
    def get_user_identity(cls, instance_config):
        """
        Parse user identity out of init_config

        To guarantee a uniquely identifiable user, expects
        {"user": {"name": "my_username", "password": "my_password",
                  "domain": {"id": "my_domain_id"}
                  }
        }
        """
        user = instance_config.get('user')

        if not (
            user and user.get('name') and user.get('password') and user.get("domain") and user.get("domain").get("id")
        ):
            raise IncompleteIdentity()

        identity = {"methods": ['password'], "password": {"user": user}}
        return identity

    @classmethod
    def get_auth_scope(cls, instance_config):
        """
        Parse authorization scope out of init_config

        To guarantee a uniquely identifiable scope, expects either:
        {'project': {'name': 'my_project', 'domain': {'id': 'my_domain_id'}}}
        OR
        {'project': {'id': 'my_project_id'}}
        """
        auth_scope = instance_config.get('auth_scope')
        if not auth_scope:
            return None

        if not auth_scope.get('project'):
            raise IncompleteAuthScope()

        if auth_scope['project'].get('name'):
            # We need to add a domain scope to avoid name clashes. Search for one. If not raise IncompleteAuthScope
            if not auth_scope['project'].get('domain', {}).get('id'):
                raise IncompleteAuthScope()
        else:
            # Assume a unique project id has been given
            if not auth_scope['project'].get('id'):
                raise IncompleteAuthScope()

        return auth_scope

    @classmethod
    def get_auth_response_from_config(cls, init_config, instance_config, proxy_config=None):
        keystone_server_url = init_config.get("keystone_server_url")
        if not keystone_server_url:
            raise IncompleteConfig()

        ssl_verify = is_affirmative(init_config.get("ssl_verify", False))

        auth_scope = cls.get_auth_scope(instance_config)
        identity = cls.get_user_identity(instance_config)

        exception_msg = None
        try:
            auth_resp = cls.request_auth_token(auth_scope, identity, keystone_server_url, ssl_verify, proxy_config)
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            exception_msg = "Failed keystone auth with user:{user} domain:{domain} scope:{scope} @{url}".format(
                user=identity['password']['user']['name'],
                domain=identity['password']['user']['domain']['id'],
                scope=auth_scope,
                url=keystone_server_url,
            )

        if exception_msg:
            try:
                identity['password']['user']['domain']['name'] = identity['password']['user']['domain'].pop('id')

                if auth_scope:
                    if 'domain' in auth_scope['project']:
                        auth_scope['project']['domain']['name'] = auth_scope['project']['domain'].pop('id')
                    else:
                        auth_scope['project']['name'] = auth_scope['project'].pop('id')
                auth_resp = cls.request_auth_token(auth_scope, identity, keystone_server_url, ssl_verify, proxy_config)
            except (
                requests.exceptions.HTTPError,
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
            ) as e:
                exception_msg = "{msg} and also failed keystone auth with \
                identity:{user} domain:{domain} scope:{scope} @{url}: {ex}".format(
                    msg=exception_msg,
                    user=identity['password']['user']['name'],
                    domain=identity['password']['user']['domain']['name'],
                    scope=auth_scope,
                    url=keystone_server_url,
                    ex=e,
                )
                raise KeystoneUnreachable(exception_msg)

        return auth_scope, auth_resp.headers.get('X-Subject-Token'), auth_resp


class OpenStackUnscoped(OpenStackScope):
    def __init__(self, auth_token, project_scope_map):
        super(OpenStackUnscoped, self).__init__(auth_token)
        self.project_scope_map = project_scope_map

    @classmethod
    def from_config(cls, init_config, instance_config, proxy_config=None):
        keystone_server_url = init_config.get("keystone_server_url")
        if not keystone_server_url:
            raise IncompleteConfig()

        ssl_verify = is_affirmative(init_config.get("ssl_verify", True))
        nova_api_version = init_config.get("nova_api_version", DEFAULT_NOVA_API_VERSION)

        _, auth_token, _ = cls.get_auth_response_from_config(init_config, instance_config, proxy_config)

        try:
            project_resp = cls.request_project_list(auth_token, keystone_server_url, ssl_verify, proxy_config)
            projects = project_resp.json().get('projects')
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            exception_msg = "unable to retrieve project list from keystone auth with identity: @{url}: {ex}".format(
                url=keystone_server_url, ex=e
            )
            raise KeystoneUnreachable(exception_msg)

        project_scope_map = {}
        for project in projects:
            try:
                project_key = project['name'], project['id']
                token_resp = cls.get_token_for_project(
                    auth_token, project, keystone_server_url, ssl_verify, proxy_config
                )
                project_auth_token = token_resp.headers.get('X-Subject-Token')
            except (
                requests.exceptions.HTTPError,
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
            ) as e:
                exception_msg = "unable to retrieve project from keystone auth with identity: @{url}: {ex}".format(
                    url=keystone_server_url, ex=e
                )
                raise KeystoneUnreachable(exception_msg)

            try:
                service_catalog = KeystoneCatalog.from_auth_response(token_resp.json(), nova_api_version)
            except MissingNovaEndpoint:
                service_catalog = KeystoneCatalog.from_auth_response(token_resp.json(), FALLBACK_NOVA_API_VERSION)

            project_auth_scope = {
                'project': {
                    'name': project['name'],
                    'id': project['id'],
                    'domain': {} if project['domain_id'] is None else {'id': project['domain_id']},
                }
            }
            project_scope = OpenStackProjectScope(project_auth_token, project_auth_scope, service_catalog)
            project_scope_map[project_key] = project_scope

        return cls(auth_token, project_scope_map)

    @classmethod
    def get_token_for_project(cls, auth_token, project, keystone_server_url, ssl_verify, proxy=None):
        identity = {"methods": ['token'], "token": {"id": auth_token}}
        scope = {'project': {'id': project['id']}}
        payload = {'auth': {'identity': identity, 'scope': scope}}
        headers = {'Content-Type': 'application/json'}
        auth_url = urljoin(keystone_server_url, "{}/auth/tokens".format(DEFAULT_KEYSTONE_API_VERSION))

        resp = requests.post(
            auth_url,
            headers=headers,
            data=json.dumps(payload),
            verify=ssl_verify,
            timeout=DEFAULT_API_REQUEST_TIMEOUT,
            proxies=proxy,
        )
        resp.raise_for_status()

        return resp

    @classmethod
    def request_project_list(cls, auth_token, keystone_server_url, ssl_verify, proxy=None):
        auth_url = urljoin(keystone_server_url, "{}/auth/projects".format(DEFAULT_KEYSTONE_API_VERSION))
        headers = {'X-Auth-Token': auth_token}

        resp = requests.get(
            auth_url, headers=headers, verify=ssl_verify, timeout=DEFAULT_API_REQUEST_TIMEOUT, proxies=proxy
        )
        resp.raise_for_status()

        return resp


class OpenStackProjectScope(OpenStackScope):
    """
    Container class for a single project's authorization scope
    Embeds the auth token to be included with API requests, and refreshes
    the token on expiry
    """

    def __init__(self, auth_token, auth_scope, service_catalog):
        super(OpenStackProjectScope, self).__init__(auth_token)

        # Store some identifiers for this project
        self.project_name = auth_scope["project"].get("name")
        self.domain_id = auth_scope["project"].get("domain", {}).get("id")
        self.tenant_id = auth_scope["project"].get("id")
        self.service_catalog = service_catalog

    @classmethod
    def from_config(cls, init_config, instance_config, proxy_config=None):
        keystone_server_url = init_config.get("keystone_server_url")
        if not keystone_server_url:
            raise IncompleteConfig()

        nova_api_version = init_config.get("nova_api_version", DEFAULT_NOVA_API_VERSION)

        auth_scope, auth_token, auth_resp = cls.get_auth_response_from_config(
            init_config, instance_config, proxy_config
        )

        try:
            service_catalog = KeystoneCatalog.from_auth_response(auth_resp.json(), nova_api_version)
        except MissingNovaEndpoint:
            service_catalog = KeystoneCatalog.from_auth_response(auth_resp.json(), FALLBACK_NOVA_API_VERSION)

        # (NOTE): aaditya
        # In some cases, the nova url is returned without the tenant id suffixed
        # e.g. http://172.0.0.1:8774 rather than http://172.0.0.1:8774/<tenant_id>
        # It is still unclear when this happens, but for now the user can configure
        # `append_tenant_id` to manually add this suffix for downstream requests
        if is_affirmative(instance_config.get("append_tenant_id", False)):
            t_id = auth_scope["project"].get("id")

            assert (
                t_id and t_id not in service_catalog.nova_endpoint
            ), """Incorrect use of append_tenant_id, please inspect the service catalog response of your Identity server.
                   You may need to disable this flag if your Nova service url contains the tenant_id already"""

            service_catalog.nova_endpoint = urljoin(service_catalog.nova_endpoint, t_id)

        return cls(auth_token, auth_scope, service_catalog)


class KeystoneCatalog(object):
    """
    A registry of services, scoped to the project, returned by the identity server
    Contains parsers for retrieving service endpoints from the server auth response
    """

    def __init__(self, nova_endpoint, neutron_endpoint):
        self.nova_endpoint = nova_endpoint
        self.neutron_endpoint = neutron_endpoint

    @classmethod
    def from_auth_response(cls, json_response, nova_api_version, keystone_server_url=None, auth_token=None, proxy=None):
        try:
            return cls(
                nova_endpoint=cls.get_nova_endpoint(json_response, nova_api_version),
                neutron_endpoint=cls.get_neutron_endpoint(json_response),
            )
        except (MissingNeutronEndpoint, MissingNovaEndpoint) as e:
            if keystone_server_url and auth_token:
                return cls.from_unscoped_token(keystone_server_url, auth_token, nova_api_version, proxy)
            else:
                raise e

    @classmethod
    def from_unscoped_token(cls, keystone_server_url, auth_token, nova_api_version, ssl_verify=True, proxy=None):
        catalog_url = urljoin(keystone_server_url, "{}/auth/catalog".format(DEFAULT_KEYSTONE_API_VERSION))
        headers = {'X-Auth-Token': auth_token}

        resp = requests.get(
            catalog_url, headers=headers, verify=ssl_verify, timeout=DEFAULT_API_REQUEST_TIMEOUT, proxies=proxy
        )
        resp.raise_for_status()
        json_resp = resp.json()
        json_resp = {'token': json_resp}

        return cls(
            nova_endpoint=cls.get_nova_endpoint(json_resp, nova_api_version),
            neutron_endpoint=cls.get_neutron_endpoint(json_resp),
        )

    @classmethod
    def get_neutron_endpoint(cls, json_resp):
        """
        Parse the service catalog returned by the Identity API for an endpoint matching the Neutron service
        Sends a CRITICAL service check when none are found registered in the Catalog
        """
        catalog = json_resp.get('token', {}).get('catalog', [])
        match = 'neutron'

        neutron_endpoint = None
        for entry in catalog:
            if entry['name'] == match or 'Networking' in entry['name']:
                valid_endpoints = {}
                for ep in entry['endpoints']:
                    interface = ep.get('interface', '')
                    if interface in ['public', 'internal']:
                        valid_endpoints[interface] = ep['url']

                if valid_endpoints:
                    # Favor public endpoints over internal
                    neutron_endpoint = valid_endpoints.get("public", valid_endpoints.get("internal"))
                    break
        else:
            raise MissingNeutronEndpoint()

        return neutron_endpoint

    @classmethod
    def get_nova_endpoint(cls, json_resp, nova_api_version=None):
        """
        Parse the service catalog returned by the Identity API for an endpoint matching
        the Nova service with the requested version
        Sends a CRITICAL service check when no viable candidates are found in the Catalog
        """
        nova_version = nova_api_version or DEFAULT_NOVA_API_VERSION
        catalog = json_resp.get('token', {}).get('catalog', [])

        nova_match = 'novav21' if nova_version == V21_NOVA_API_VERSION else 'nova'

        for entry in catalog:
            if entry['name'] == nova_match or 'Compute' in entry['name']:
                # Collect any endpoints on the public or internal interface
                valid_endpoints = {}
                for ep in entry['endpoints']:
                    interface = ep.get('interface', '')
                    if interface in ['public', 'internal']:
                        valid_endpoints[interface] = ep['url']

                if valid_endpoints:
                    # Favor public endpoints over internal
                    nova_endpoint = valid_endpoints.get("public", valid_endpoints.get("internal"))
                    return nova_endpoint
        else:
            raise MissingNovaEndpoint()


class OpenStackControllerCheck(AgentCheck):
    CACHE_TTL = {"aggregates": 300, "physical_hosts": 300, "hypervisors": 300}  # seconds

    FETCH_TIME_ACCESSORS = {
        "aggregates": "_last_aggregate_fetch_time",
        "physical_hosts": "_last_host_fetch_time",
        "hypervisors": "_last_hypervisor_fetch_time",
    }

    HYPERVISOR_STATE_UP = 'up'
    HYPERVISOR_STATE_DOWN = 'down'
    NETWORK_STATE_UP = 'UP'

    NETWORK_API_SC = 'openstack.neutron.api.up'
    COMPUTE_API_SC = 'openstack.nova.api.up'
    IDENTITY_API_SC = 'openstack.keystone.api.up'

    # Service checks for individual hypervisors and networks
    HYPERVISOR_SC = 'openstack.nova.hypervisor.up'
    NETWORK_SC = 'openstack.neutron.network.up'

    HYPERVISOR_CACHE_EXPIRY = 120  # seconds

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        self._ssl_verify = is_affirmative(init_config.get("ssl_verify", True))
        self.keystone_server_url = init_config.get("keystone_server_url")
        self._hypervisor_name_cache = {}

        self.paginated_server_limit = init_config.get('paginated_server_limit') or DEFAULT_PAGINATED_SERVER_LIMIT

        self.request_timeout = init_config.get('request_timeout') or DEFAULT_API_REQUEST_TIMEOUT

        if not self.keystone_server_url:
            raise IncompleteConfig()

        # Current authentication scopes
        self._parent_scope = None
        self._current_scope = None

        # Cache some things between runs for values that change rarely
        self._aggregate_list = None

        # Mapping of check instances to associated OpenStack project scopes
        self.instance_map = {}

        # Mapping of Nova-managed servers to tags
        self.external_host_tags = {}

        self.exclude_network_id_rules = set([re.compile(ex) for ex in init_config.get('exclude_network_ids', [])])
        self.exclude_server_id_rules = set([re.compile(ex) for ex in init_config.get('exclude_server_ids', [])])
        self.include_project_name_rules = set([re.compile(ex) for ex in init_config.get('whitelist_project_names', [])])
        self.exclude_project_name_rules = set([re.compile(ex) for ex in init_config.get('blacklist_project_names', [])])

        skip_proxy = not is_affirmative(init_config.get('use_agent_proxy', True))
        self.proxy_config = None if skip_proxy else self.proxies

        self.backoff = {}
        random.seed()

        # ISO8601 date time: used to filter the call to get the list of nova servers
        self.changes_since_time = {}

        # Ex: server_details_by_id = {
        #   UUID: {UUID: <value>, etc}
        #   1: {id: 1, name: hostA},
        #   2: {id: 2, name: hostB}
        # }
        self.server_details_by_id = {}

    def _make_request_with_auth_fallback(self, url, headers=None, params=None, timeout=DEFAULT_API_REQUEST_TIMEOUT):
        """
        Generic request handler for OpenStack API requests
        Raises specialized Exceptions for commonly encountered error codes
        """
        self.log.debug("Request URL and Params: %s, %s", url, params)
        try:
            resp = requests.get(
                url,
                headers=headers,
                verify=self._ssl_verify,
                params=params,
                timeout=timeout,
                proxies=self.proxy_config,
            )
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            self.log.debug("Error contacting openstack endpoint: %s", e)
            if resp.status_code == 401:
                self.log.info('Need to reauthenticate before next check')

                # Delete the scope, we'll populate a new one on the next run for this instance
                self.delete_current_scope()
            elif resp.status_code == 409:
                raise InstancePowerOffFailure()
            else:
                raise e

        return resp.json()

    def _instance_key(self, instance):
        i_key = instance.get('name')
        if not i_key:
            # We need a name to identify this instance
            raise IncompleteConfig()
        return i_key

    def delete_current_scope(self):
        scope_to_delete = self._parent_scope if self._parent_scope else self._current_scope
        for i_key, scope in list(iteritems(self.instance_map)):
            if scope is scope_to_delete:
                self.log.debug("Deleting current scope: %s", i_key)
                del self.instance_map[i_key]

    def should_run(self, instance):
        i_key = self._instance_key(instance)
        if i_key not in self.backoff:
            self.backoff[i_key] = {'retries': 0, 'scheduled': time.time()}

        if self.backoff[i_key]['scheduled'] <= time.time():
            return True

        return False

    def do_backoff(self, instance):
        i_key = self._instance_key(instance)
        tracker = self.backoff[i_key]

        self.backoff[i_key]['retries'] += 1
        jitter = min(MAX_BACKOFF_SECS, BASE_BACKOFF_SECS * 2 ** self.backoff[i_key]['retries'])

        # let's add some jitter  (half jitter)
        backoff_interval = jitter / 2
        backoff_interval += random.randint(0, backoff_interval)

        tags = instance.get('tags', [])
        hypervisor_name = self._hypervisor_name_cache.get(i_key)
        if hypervisor_name:
            tags.extend("hypervisor:{}".format(hypervisor_name))

        self.gauge("openstack.backoff.interval", backoff_interval, tags=tags)
        self.gauge("openstack.backoff.retries", self.backoff[i_key]['retries'], tags=tags)

        tracker['scheduled'] = time.time() + backoff_interval

    def reset_backoff(self, instance):
        i_key = self._instance_key(instance)
        self.backoff[i_key]['retries'] = 0
        self.backoff[i_key]['scheduled'] = time.time()

    def get_scope_for_instance(self, instance):
        i_key = self._instance_key(instance)
        self.log.debug("Getting scope for instance %s", i_key)
        return self.instance_map[i_key]

    def set_scope_for_instance(self, instance, scope):
        i_key = self._instance_key(instance)
        self.log.debug("Setting scope for instance %s", i_key)
        self.instance_map[i_key] = scope

    def delete_scope_for_instance(self, instance):
        i_key = self._instance_key(instance)
        self.log.debug("Deleting scope for instance %s", i_key)
        del self.instance_map[i_key]

    def get_auth_token(self, instance=None):
        if not instance:
            # Assume instance scope is populated on self
            return self._current_scope.auth_token

        return self.get_scope_for_instance(instance).auth_token

    # Network
    def get_neutron_endpoint(self, instance=None):
        if not instance:
            # Assume instance scope is populated on self
            return self._current_scope.service_catalog.neutron_endpoint

        return self.get_scope_for_instance(instance).service_catalog.neutron_endpoint

    def get_network_stats(self, tags):
        """
        Collect stats for all reachable networks
        """

        # FIXME: (aaditya) Check all networks defaults to true
        # until we can reliably assign agents to networks to monitor
        if is_affirmative(self.init_config.get('check_all_networks', True)):
            all_network_ids = set(self.get_all_network_ids())

            # Filter out excluded networks
            network_ids = [
                network_id
                for network_id in all_network_ids
                if not any([re.match(exclude_id, network_id) for exclude_id in self.exclude_network_id_rules])
            ]
        else:
            network_ids = self.init_config.get('network_ids', [])

        if not network_ids:
            self.warning(
                "Your check is not configured to monitor any networks.\n"
                + "Please list `network_ids` under your init_config"
            )

        for nid in network_ids:
            self.get_stats_for_single_network(nid, tags)

    def get_all_network_ids(self):
        url = '{}/{}/networks'.format(self.get_neutron_endpoint(), DEFAULT_NEUTRON_API_VERSION)
        headers = {'X-Auth-Token': self.get_auth_token()}

        network_ids = []
        try:
            net_details = self._make_request_with_auth_fallback(url, headers)
            for network in net_details['networks']:
                network_ids.append(network['id'])
        except Exception as e:
            self.warning('Unable to get the list of all network ids: {}'.format(str(e)))
            raise e

        return network_ids

    def get_stats_for_single_network(self, network_id, tags):
        url = '{}/{}/networks/{}'.format(self.get_neutron_endpoint(), DEFAULT_NEUTRON_API_VERSION, network_id)
        headers = {'X-Auth-Token': self.get_auth_token()}
        net_details = self._make_request_with_auth_fallback(url, headers)

        service_check_tags = ['network:{}'.format(network_id)] + tags

        network_name = net_details.get('network', {}).get('name')
        if network_name:
            service_check_tags.append('network_name:{}'.format(network_name))

        tenant_id = net_details.get('network', {}).get('tenant_id')
        if tenant_id:
            service_check_tags.append('tenant_id:{}'.format(tenant_id))

        if net_details.get('network', {}).get('admin_state_up'):
            self.service_check(self.NETWORK_SC, AgentCheck.OK, tags=service_check_tags)
        else:
            self.service_check(self.NETWORK_SC, AgentCheck.CRITICAL, tags=service_check_tags)

    # Compute
    def get_nova_endpoint(self, instance=None):
        if not instance:
            # Assume instance scope is populated on self
            return self._current_scope.service_catalog.nova_endpoint

        return self.get_scope_for_instance(instance).service_catalog.nova_endpoint

    def _parse_uptime_string(self, uptime):
        """ Parse u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n' """
        uptime = uptime.strip()
        load_averages = uptime[uptime.find('load average:'):].split(':')[1].strip().split(',')
        load_averages = [float(load_avg) for load_avg in load_averages]
        uptime_sec = uptime.split(',')[0]
        return {'loads': load_averages, 'uptime_sec': uptime_sec}

    def get_all_aggregate_hypervisors(self):
        url = '{}/os-aggregates'.format(self.get_nova_endpoint())
        headers = {'X-Auth-Token': self.get_auth_token()}

        hypervisor_aggregate_map = {}
        try:
            aggregate_list = self._make_request_with_auth_fallback(url, headers)
            for v in aggregate_list['aggregates']:
                for host in v['hosts']:
                    hypervisor_aggregate_map[host] = {
                        'aggregate': v['name'],
                        'availability_zone': v['availability_zone'],
                    }

        except Exception as e:
            self.warning('Unable to get the list of aggregates: {}'.format(str(e)))
            raise e

        return hypervisor_aggregate_map

    def get_uptime_for_single_hypervisor(self, hyp_id):
        url = '{}/os-hypervisors/{}/uptime'.format(self.get_nova_endpoint(), hyp_id)
        headers = {'X-Auth-Token': self.get_auth_token()}

        resp = self._make_request_with_auth_fallback(url, headers)
        uptime = resp['hypervisor']['uptime']
        return self._parse_uptime_string(uptime)

    def get_stats_for_all_hypervisors(self, instance, custom_tags=None,
                                      use_shortname=False,
                                      collect_hypervisor_load=False):
        """
        Submits stats for all hypervisors registered to this control plane
        Raises specific exceptions based on response code
        """
        url = '{}/os-hypervisors/detail'.format(self.get_nova_endpoint())
        headers = {'X-Auth-Token': self.get_auth_token()}
        resp = self._make_request_with_auth_fallback(url, headers)
        hypervisors = resp.get('hypervisors', [])
        for hyp in hypervisors:
            self.get_stats_for_single_hypervisor(hyp, instance, custom_tags=custom_tags,
                                                 use_shortname=use_shortname,
                                                 collect_hypervisor_load=collect_hypervisor_load)

        if not hypervisors:
            self.log.warn("Unable to collect any hypervisors from Nova response: {}".format(resp))

    def get_stats_for_single_hypervisor(self, hyp, instance, custom_tags=None,
                                        use_shortname=False,
                                        collect_hypervisor_load=False):
        hyp_hostname = hyp.get('hypervisor_hostname')
        self._hypervisor_name_cache[self._instance_key(instance)] = hyp_hostname
        custom_tags = custom_tags or []
        tags = [
            'hypervisor:{}'.format(hyp_hostname),
            'hypervisor_id:{}'.format(hyp['id']),
            'virt_type:{}'.format(hyp['hypervisor_type']),
            'status:{}'.format(hyp['status']),
        ]
        host_tags = self._get_host_aggregate_tag(hyp_hostname,
                                                 use_shortname=use_shortname)
        tags.extend(host_tags)
        tags.extend(custom_tags)
        service_check_tags = list(custom_tags)

        # This makes a request per hypervisor and only sends hypervisor_load 1/5/15
        # Disable this by default for higher performance in a large environment
        # If the Agent is installed on the hypervisors, system.load.1/5/15 is available
        if collect_hypervisor_load:
            try:
                uptime = self.get_uptime_for_single_hypervisor(hyp['id'])
            except Exception as e:
                self.warning('Unable to get uptime for hypervisor {}: {}'.format(hyp['id'], str(e)))
                uptime = {}

            load_averages = uptime.get("loads")
            if load_averages and len(load_averages) == 3:
                for i, avg in enumerate([1, 5, 15]):
                    self.gauge('openstack.nova.hypervisor_load.{}'.format(avg), load_averages[i], tags=tags)
            else:
                self.log.debug("Load Averages didn't return expected values: {}".format(load_averages))

        hyp_state = hyp.get('state', None)

        if not hyp_state:
            self.service_check(self.HYPERVISOR_SC, AgentCheck.UNKNOWN, hostname=hyp_hostname, tags=service_check_tags)
        elif hyp_state != self.HYPERVISOR_STATE_UP:
            self.service_check(self.HYPERVISOR_SC, AgentCheck.CRITICAL, hostname=hyp_hostname, tags=service_check_tags)
        else:
            self.service_check(self.HYPERVISOR_SC, AgentCheck.OK, hostname=hyp_hostname, tags=service_check_tags)

        for label, val in iteritems(hyp):
            if label in NOVA_HYPERVISOR_METRICS:
                metric_label = "openstack.nova.{}".format(label)
                self.gauge(metric_label, val, tags=tags)

    # Get all of the server IDs and their metadata and cache them
    # After the first run, we will only get servers that have changed state since the last collection run
    def get_all_servers(self, i_key):
        query_params = {}

        # If we don't have a timestamp for this instance, default to None
        if i_key in self.changes_since_time:
            query_params['changes-since'] = self.changes_since_time.get(i_key)

        url = '{}/servers/detail'.format(self.get_nova_endpoint())
        headers = {'X-Auth-Token': self.get_auth_token()}

        # Note this query param specifically requires admin user rights
        query_params["all_tenants"] = True
        servers = []

        try:
            # Get a list of active servers using pagination
            query_params['status'] = 'ACTIVE'
            query_params['limit'] = self.paginated_server_limit
            resp = self._make_request_with_auth_fallback(
                url, headers, params=query_params, timeout=self.request_timeout
            )
            servers.extend(resp['servers'])
            # Avoid the extra request since we know we're done when the response has anywhere between
            # 0 and paginated_server_limit servers
            while len(resp['servers']) == self.paginated_server_limit:
                query_params['marker'] = resp['servers'][-1]['id']
                resp = self._make_request_with_auth_fallback(
                    url, headers, params=query_params, timeout=self.request_timeout
                )
                servers.extend(resp['servers'])

            query_params['limit'] = None
            query_params['marker'] = None

            # Don't collect Deleted or Shut off VMs on the first run:
            if i_key in self.changes_since_time:

                # Get a list of deleted serversTimestamp used to filter the call to get the list
                # Need to have admin perms for this to take affect
                query_params['deleted'] = 'true'
                del query_params['status']
                resp = self._make_request_with_auth_fallback(url, headers, params=query_params)

                servers.extend(resp['servers'])
                query_params['deleted'] = 'false'

                # Get a list of shut off servers
                query_params['status'] = 'SHUTOFF'
                resp = self._make_request_with_auth_fallback(url, headers, params=query_params)
                servers.extend(resp['servers'])

            self.changes_since_time[i_key] = datetime.utcnow().isoformat()

        except Exception as e:
            self.warning('Unable to get the list of all servers: {}'.format(str(e)))
            raise e

        for server in servers:
            new_server = {}
            new_server['server_id'] = server.get('id')
            new_server['state'] = server.get('status')
            new_server['server_name'] = server.get('name')
            new_server['hypervisor_hostname'] = server.get('OS-EXT-SRV-ATTR:hypervisor_hostname')
            new_server['tenant_id'] = server.get('tenant_id')
            new_server['availability_zone'] = server.get('OS-EXT-AZ:availability_zone')

            # Confirm that the new server has all the required fields
            if not all(key in new_server for key in SERVER_FIELDS_REQ):
                self.log.debug("Server {} is missing one of the required keys. Not adding to cache".format(new_server))
                continue

            # Update our cached list of servers
            if (
                new_server['server_id'] not in self.server_details_by_id
                and new_server['state'] in DIAGNOSTICABLE_STATES
            ):
                self.log.debug("Adding server to cache: %s", new_server)
                # The project may not exist if the server isn't in an active state
                # Query for the project name here to avoid 404s
                # If the project name conversion fails, we won't add this server
                new_server['project_name'] = self.get_project_name_from_id(new_server['tenant_id'])
                if new_server['project_name']:
                    self.server_details_by_id[new_server['server_id']] = new_server
            elif new_server['server_id'] in self.server_details_by_id and new_server['state'] in REMOVED_STATES:
                self.log.debug("Removing server from cache: %s", new_server)
                try:
                    del self.server_details_by_id[new_server['server_id']]
                except KeyError as e:
                    self.log.debug("Server: %s has already been removed from the cache", new_server['server_id'])

    def filter_excluded_servers(self):
        proj_list = set([])
        if self.exclude_server_id_rules:
            # Filter out excluded servers
            for exclude_id_rule in self.exclude_server_id_rules:
                for server_id in list(self.server_details_by_id):
                    if re.match(exclude_id_rule, server_id):
                        del self.server_details_by_id[server_id]

        for _, server in iteritems(self.server_details_by_id):
            proj_list.add(server.get('project_name'))

        projects_filtered = pattern_filter(
            proj_list,
            whitelist=self.include_project_name_rules,
            blacklist=self.exclude_project_name_rules
        )

        self.server_details_by_id = {
                sid: server for (sid, server)
                in iteritems(self.server_details_by_id)
                if server.get('project_name') in projects_filtered
        }

    def get_project_name_from_id(self, tenant_id):
        url = "{}/{}/{}/{}".format(self.keystone_server_url, DEFAULT_KEYSTONE_API_VERSION, "projects", tenant_id)
        self.log.debug("Project URL is %s", url)
        headers = {'X-Auth-Token': self.get_auth_token()}
        try:
            r = self._make_request_with_auth_fallback(url, headers)
            return r['project']['name']

        except Exception as e:
            self.warning('Unable to get project name: {}'.format(str(e)))
            return None

    def get_stats_for_single_server(self, server_details, tags=None, use_shortname=False):
        def _is_valid_metric(label):
            return label in NOVA_SERVER_METRICS or any(seg in label for seg in NOVA_SERVER_INTERFACE_SEGMENTS)

        hypervisor_hostname = server_details.get('hypervisor_hostname')
        host_tags = self._get_host_aggregate_tag(hypervisor_hostname, use_shortname=use_shortname)
        host_tags.append('availability_zone:{}'.format(server_details.get('availability_zone', 'NA')))
        self.external_host_tags[server_details.get('server_name')] = host_tags

        server_id = server_details.get('server_id')
        server_name = server_details.get('server_name')
        hypervisor_hostname = server_details.get('hypervisor_hostname')
        project_name = server_details.get('project_name')

        server_stats = {}
        headers = {'X-Auth-Token': self.get_auth_token()}
        url = '{}/servers/{}/diagnostics'.format(self.get_nova_endpoint(), server_id)
        try:
            server_stats = self._make_request_with_auth_fallback(url, headers)
        except InstancePowerOffFailure:  # 409 response code came back fro nova
            self.log.debug("Server %s is powered off and cannot be monitored", server_id)
            del self.server_details_by_id[server_id]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.log.debug("Server %s is not in an ACTIVE state and cannot be monitored, %s", server_id, e)
                del self.server_details_by_id[server_id]
            else:
                self.log.debug("Received HTTP Error when reaching the nova endpoint")
                return
        except Exception as e:
            self.warning("Unknown error when monitoring %s : %s" % (server_id, e))
            return

        if server_stats:
            tags = tags or []
            if project_name:
                tags.append("project_name:{}".format(project_name))
            if hypervisor_hostname:
                tags.append("hypervisor:{}".format(hypervisor_hostname))
            if server_name:
                tags.append("server_name:{}".format(server_name))
            for st in server_stats:
                if _is_valid_metric(st):
                    self.gauge(
                        "openstack.nova.server.{}".format(st.replace("-", "_")),
                        server_stats[st],
                        tags=tags+host_tags,
                        hostname=server_id,
                    )

    def get_stats_for_single_project(self, project, tags=None):
        def _is_valid_metric(label):
            return label in PROJECT_METRICS

        if tags is None:
            tags = []

        server_tags = copy.deepcopy(tags)
        project_name = project.get('name')
        project_id = project.get('id')

        self.log.debug("Collecting metrics for project. name: {} id: {}".format(project_name, project['id']))

        url = '{}/limits'.format(self.get_nova_endpoint())
        headers = {'X-Auth-Token': self.get_auth_token()}
        server_stats = self._make_request_with_auth_fallback(url, headers, params={"tenant_id": project['id']})

        server_tags.append('tenant_id:{}'.format(project_id))

        if project_name:
            server_tags.append('project_name:{}'.format(project_name))

        try:
            for st in server_stats['limits']['absolute']:
                if _is_valid_metric(st):
                    metric_key = PROJECT_METRICS[st]
                    self.gauge(
                        "openstack.nova.limits.{}".format(metric_key),
                        server_stats['limits']['absolute'][st],
                        tags=server_tags,
                    )
        except KeyError:
            self.log.warn("{} returned unexpected response, not submitting limits metrics".format(url))

    # Cache util
    def _is_expired(self, entry):
        assert entry in ["aggregates", "physical_hosts", "hypervisors"]
        ttl = self.CACHE_TTL.get(entry)
        last_fetch_time = getattr(self, self.FETCH_TIME_ACCESSORS.get(entry))
        return datetime.now() - last_fetch_time > timedelta(seconds=ttl)

    def _get_and_set_aggregate_list(self):
        if not self._aggregate_list or self._is_expired("aggregates"):
            self._aggregate_list = self.get_all_aggregate_hypervisors()
            self._last_aggregate_fetch_time = datetime.now()

        return self._aggregate_list

    def _send_api_service_checks(self, scope, tags):
        # Nova
        headers = {"X-Auth-Token": scope.auth_token}

        try:
            requests.get(
                scope.service_catalog.nova_endpoint,
                headers=headers,
                verify=self._ssl_verify,
                timeout=DEFAULT_API_REQUEST_TIMEOUT,
                proxies=self.proxy_config,
            )
            self.service_check(
                self.COMPUTE_API_SC,
                AgentCheck.OK,
                tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + tags,
            )
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            self.service_check(
                self.COMPUTE_API_SC,
                AgentCheck.CRITICAL,
                tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + tags,
            )

        # Neutron
        try:
            requests.get(
                scope.service_catalog.neutron_endpoint,
                headers=headers,
                verify=self._ssl_verify,
                timeout=DEFAULT_API_REQUEST_TIMEOUT,
                proxies=self.proxy_config,
            )
            self.service_check(
                self.NETWORK_API_SC,
                AgentCheck.OK,
                tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + tags,
            )
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            self.service_check(
                self.NETWORK_API_SC,
                AgentCheck.CRITICAL,
                tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + tags,
            )

    def ensure_auth_scope(self, instance):
        """
        Guarantees a valid auth scope for this instance, and returns it

        Communicates with the identity server and initializes a new scope when one is absent, or has been forcibly
        removed due to token expiry
        """
        instance_scope = None

        custom_tags = instance.get('tags', [])
        if custom_tags is None:
            custom_tags = []
        try:
            instance_scope = self.get_scope_for_instance(instance)
        except KeyError:

            # We're missing a project scope for this instance
            # Let's populate it now
            try:
                if 'auth_scope' in instance:
                    instance_scope = OpenStackProjectScope.from_config(self.init_config, instance, self.proxy_config)
                else:
                    instance_scope = OpenStackUnscoped.from_config(self.init_config, instance, self.proxy_config)

                self.service_check(
                    self.IDENTITY_API_SC,
                    AgentCheck.OK,
                    tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + custom_tags,
                )
            except KeystoneUnreachable as e:
                self.warning(
                    "The agent could not contact the specified identity server at %s . \
                    Are you sure it is up at that address?"
                    % self.init_config.get("keystone_server_url")
                )
                self.log.debug("Problem grabbing auth token: %s", e)
                self.service_check(
                    self.IDENTITY_API_SC,
                    AgentCheck.CRITICAL,
                    tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + custom_tags,
                )

                # If Keystone is down/unreachable, we default the
                # Nova and Neutron APIs to UNKNOWN since we cannot access the service catalog
                self.service_check(
                    self.NETWORK_API_SC,
                    AgentCheck.UNKNOWN,
                    tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + custom_tags,
                )
                self.service_check(
                    self.COMPUTE_API_SC,
                    AgentCheck.UNKNOWN,
                    tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + custom_tags,
                )

            except MissingNovaEndpoint as e:
                self.warning("The agent could not find a compatible Nova endpoint in your service catalog!")
                self.log.debug("Failed to get nova endpoint for response catalog: %s", e)
                self.service_check(
                    self.COMPUTE_API_SC,
                    AgentCheck.CRITICAL,
                    tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + custom_tags,
                )

            except MissingNeutronEndpoint:
                self.warning("The agent could not find a compatible Neutron endpoint in your service catalog!")
                self.service_check(
                    self.NETWORK_API_SC,
                    AgentCheck.CRITICAL,
                    tags=["keystone_server:%s" % self.init_config.get("keystone_server_url")] + custom_tags,
                )
            else:
                self.set_scope_for_instance(instance, instance_scope)

        return instance_scope

    def check(self, instance):
        # have we been backed off
        if not self.should_run(instance):
            self.log.info('Skipping run due to exponential backoff in effect')
            return

        projects = {}
        custom_tags = instance.get("tags", [])
        collect_limits_from_all_projects = is_affirmative(instance.get('collect_limits_from_all_projects', True))
        collect_hypervisor_load = is_affirmative(instance.get('collect_hypervisor_load', False))
        use_shortname = is_affirmative(instance.get('use_shortname', False))

        try:
            instance_scope = self.ensure_auth_scope(instance)
            if not instance_scope:
                # Fast fail in the absence of an instance_scope
                return

            scope_map = {}
            if isinstance(instance_scope, OpenStackProjectScope):
                #  Key could be anything but same format for consistency
                scope_key = (instance_scope.project_name, instance_scope.tenant_id)
                scope_map[scope_key] = instance_scope
                self._parent_scope = None
            elif isinstance(instance_scope, OpenStackUnscoped):
                scope_map.update(instance_scope.project_scope_map)
                self._parent_scope = instance_scope

            for _, scope in iteritems(scope_map):
                # Store the scope on the object so we don't have to keep passing it around
                self._current_scope = scope

                self._send_api_service_checks(scope, custom_tags)

                self.log.debug("Running check with credentials: \n")
                self.log.debug("Nova Url: %s", self.get_nova_endpoint())
                self.log.debug("Neutron Url: %s", self.get_neutron_endpoint())

                project = self.get_scoped_project(scope)
                if project and project.get('name'):
                    projects[project.get('name')] = project

                i_key = self._instance_key(instance)

            if collect_limits_from_all_projects:
                scope_projects = self.get_all_projects(scope)
                if scope_projects:
                    for proj in scope_projects:
                        projects[proj['name']] = proj

            proj_filtered = pattern_filter(
                [p for p in projects],
                whitelist=self.include_project_name_rules,
                blacklist=self.exclude_project_name_rules
            )

            projects = \
                {name: v for (name, v) in iteritems(projects) if name in proj_filtered}

            for name, project in iteritems(projects):
                self.get_stats_for_single_project(project, custom_tags)

            self.get_stats_for_all_hypervisors(instance, custom_tags=custom_tags,
                                               use_shortname=use_shortname,
                                               collect_hypervisor_load=collect_hypervisor_load)

            # This updates the server cache directly
            self.get_all_servers(i_key)
            self.filter_excluded_servers()

            # Deep copy the cache so we can remove things from the Original during the iteration
            # Allows us to remove bad servers from the cache if needbe
            server_cache_copy = copy.deepcopy(self.server_details_by_id)

            for server in server_cache_copy:
                server_tags = copy.deepcopy(custom_tags)
                server_tags.append("nova_managed_server")

                self.get_stats_for_single_server(server_cache_copy[server], tags=server_tags,
                                                 use_shortname=use_shortname)

            # For now, monitor all networks
            self.get_network_stats(custom_tags)

            if set_external_tags is not None:
                set_external_tags(self.get_external_host_tags())

        except IncompleteConfig as e:
            if isinstance(e, IncompleteAuthScope):
                self.warning(
                    """Please specify the auth scope via the `auth_scope` variable in your init_config.\n
                             The auth_scope should look like: \n
                            {'project': {'name': 'my_project', 'domain': {'id': 'my_domain_id'}}}\n
                            OR\n
                            {'project': {'id': 'my_project_id'}}
                             """
                )
            elif isinstance(e, IncompleteIdentity):
                self.warning(
                    "Please specify the user via the `user` variable in your init_config.\n"
                    + "This is the user you would use to authenticate with Keystone v3 via password auth.\n"
                    + "The user should look like:"
                    + "{'password': 'my_password', 'name': 'my_name', 'domain': {'id': 'my_domain_id'}}"
                )
            else:
                self.warning("Configuration Incomplete! Check your openstack.yaml file")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code >= 500:
                # exponential backoff
                self.do_backoff(instance)
                self.warning("There were some problems reaching the nova API - applying exponential backoff")
            else:
                self.warning("Error reaching nova API")

            return
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            # exponential backoff
            self.do_backoff(instance)
            self.warning("There were some problems reaching the nova API - applying exponential backoff")
            return

        self.reset_backoff(instance)

    def get_all_projects(self, scope):
        """
        Returns all projects in the domain
        """
        url = "{}/{}/{}".format(self.keystone_server_url, DEFAULT_KEYSTONE_API_VERSION, "projects")
        headers = {'X-Auth-Token': scope.auth_token}
        try:
            r = self._make_request_with_auth_fallback(url, headers)
            return r['projects']

        except Exception as e:
            self.warning('Unable to get projects: {}'.format(str(e)))
            raise e

        return None

    def get_scoped_project(self, project_auth_scope):
        """
        Returns the project that this instance of the check is scoped to
        """

        filter_params = {}
        url = "{}/{}/{}".format(self.keystone_server_url, DEFAULT_KEYSTONE_API_VERSION, "projects")
        if project_auth_scope.tenant_id:
            if project_auth_scope.project_name:
                return {"id": project_auth_scope.tenant_id, "name": project_auth_scope.project_name}

            url = "{}/{}".format(url, project_auth_scope.tenant_id)
        else:
            filter_params = {"name": project_auth_scope.project_name, "domain_id": project_auth_scope.domain_id}

        headers = {'X-Auth-Token': project_auth_scope.auth_token}

        try:
            project_details = self._make_request_with_auth_fallback(url, headers, params=filter_params)
            if filter_params:
                assert len(project_details["projects"]) == 1, "Non-unique project credentials"

                # Set the tenant_id so we won't have to fetch it next time
                project_auth_scope.tenant_id = project_details["projects"][0].get("id")
                return project_details["projects"][0]
            else:
                project_auth_scope.project_name = project_details["project"]["name"]
                return project_details["project"]

        except Exception as e:
            self.warning('Unable to get the project details: {}'.format(str(e)))
            raise e

        return None

    def _get_host_aggregate_tag(self, hyp_hostname, use_shortname=False):
        tags = []
        hyp_hostname = hyp_hostname.split('.')[0] if use_shortname else hyp_hostname
        if hyp_hostname in self._get_and_set_aggregate_list():
            tags.append('aggregate:{}'.format(self._aggregate_list[hyp_hostname].get('aggregate', "unknown")))
            # Need to check if there is a value for availability_zone
            # because it is possible to have an aggregate without an AZ
            try:
                if self._aggregate_list[hyp_hostname].get('availability_zone'):
                    tags.append('availability_zone:{}'
                                .format(self._aggregate_list[hyp_hostname]['availability_zone']))
            except KeyError:
                self.log.debug('Unable to get the availability_zone for hypervisor: {}'.format(hyp_hostname))
        else:
            self.log.info('Unable to find hostname %s in aggregate list. Assuming this host is unaggregated',
                          hyp_hostname)

        return tags

    # For attaching tags to hosts that are not the host running the agent
    def get_external_host_tags(self):
        """ Returns a list of tags for every guest server that is detected by the OpenStack
        integration.
        List of pairs (hostname, list_of_tags)
        """
        self.log.debug("Collecting external_host_tags now")
        external_host_tags = []
        for k, v in iteritems(self.external_host_tags):
            external_host_tags.append((k, {SOURCE_TYPE: v}))

        self.log.debug("Sending external_host_tags: %s", external_host_tags)
        return external_host_tags
