# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests import HTTPError, Timeout

from datadog_checks.base import AgentCheck

SERVICE_CHECK_PROCESS_CAN_CONNECT = 'druid.process.can_connect'
SERVICE_CHECK_PROCESS_STATUS = 'druid.process.status'


class DruidCheck(AgentCheck):
    def check(self, instance):
        custom_tags = instance.get('tags', [])

        base_url = instance.get('process_url')

        process_properties = self._get_process_properties(base_url, custom_tags)

        druid_service = process_properties['druid.service']
        tags = custom_tags + ['process:{}'.format(druid_service)]

        self._submit_status_service_check(base_url, tags)

    def _submit_status_service_check(self, base_url, tags):
        url = base_url + "/status/health"
        service_check_tags = ['url:{}'.format(url)] + tags

        resp = self._make_request(url)
        if resp is True:
            self.service_check(SERVICE_CHECK_PROCESS_STATUS, AgentCheck.OK, tags=service_check_tags)
        else:
            self.service_check(SERVICE_CHECK_PROCESS_STATUS, AgentCheck.CRITICAL, tags=service_check_tags)

    def _get_process_properties(self, base_url, tags):
        url = base_url + "/status/properties"
        service_check_tags = ['url:{}'.format(url)] + tags
        try:
            r = self.http.get(url)
            r.raise_for_status()
        except Exception:
            self.service_check(SERVICE_CHECK_PROCESS_CAN_CONNECT, AgentCheck.CRITICAL, tags=service_check_tags)
            raise
        self.service_check(SERVICE_CHECK_PROCESS_CAN_CONNECT, AgentCheck.OK, tags=service_check_tags)
        return r.json()

    def _make_request(self, url):
        try:
            resp = self.http.get(url)
            return resp.json()
        except (HTTPError, ConnectionError) as e:
            self.warning(
                "Couldn't connect to URL: {} with exception: {}. Please verify the address is reachable".format(url, e)
            )
        except Timeout:
            self.warning("Connection timeout when connecting to {}".format(url))


# TAGS:
#   - druid service name e.g. druid/broker

# TODO: Handle version
# etcd.server.version,gauge,,item,,Which version is running. 1 for 'server_version' label with current version.,0,etcd,
