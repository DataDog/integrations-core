# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import requests
from urlparse import urljoin

from .exceptions import MissingNeutronEndpoint, MissingNovaEndpoint
from .settings import (DEFAULT_KEYSTONE_API_VERSION, DEFAULT_API_REQUEST_TIMEOUT, DEFAULT_NOVA_API_VERSION,
                       V21_NOVA_API_VERSION)


class ServiceCatalog(object):
    """
    Acts as a endpoint discovery service.
    A registry of services, scoped to a project or not, returned by the identity server (aka: keystone)
    Contains parsers for retrieving service endpoints from the server auth response
    """

    def __init__(self, nova_endpoint, neutron_endpoint):
        self.nova_endpoint = nova_endpoint
        self.neutron_endpoint = neutron_endpoint

    @classmethod
    def from_auth_response(cls, json_response, nova_api_version, keystone_server_url=None, auth_token=None, proxy=None):
        try:
            return cls(
                nova_endpoint=cls._get_nova_endpoint(json_response, nova_api_version),
                neutron_endpoint=cls._get_neutron_endpoint(json_response),
            )
        except (MissingNeutronEndpoint, MissingNovaEndpoint) as e:
            # TODO instead of making teh call in the except part let's do one or the other.
            # This would prevent lot of unnedeed calls
            if keystone_server_url and auth_token:
                return cls.from_unscoped_token(keystone_server_url, auth_token, nova_api_version, proxy)
            else:
                raise e

    @classmethod
    def from_unscoped_token(cls, keystone_server_url, auth_token, nova_api_version, ssl_verify=True, proxy=None):
        catalog_url = urljoin(keystone_server_url, "{0}/auth/catalog".format(DEFAULT_KEYSTONE_API_VERSION))
        headers = {'X-Auth-Token': auth_token}

        resp = requests.get(
            catalog_url, headers=headers, verify=ssl_verify, timeout=DEFAULT_API_REQUEST_TIMEOUT, proxies=proxy
        )
        resp.raise_for_status()
        json_resp = resp.json()
        json_resp = {'token': json_resp}

        return cls(
            nova_endpoint=cls._get_nova_endpoint(json_resp, nova_api_version),
            neutron_endpoint=cls._get_neutron_endpoint(json_resp),
        )

    @classmethod
    def _get_neutron_endpoint(cls, json_resp):
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
    def _get_nova_endpoint(cls, json_resp, nova_api_version=None):
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
