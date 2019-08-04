# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from urllib.parse import urlparse

from datadog_checks.base import AgentCheck

SERVICE_CHECK_NAME = 'druid.can_connect'

class DruidCheck(AgentCheck):
    # TODO: Use http.RequestsWrapper

    def check(self, instance):
        custom_tags = instance.get('tags', [])

        url = instance.get('process_url')

        service_check_tags = tags_from_url(url=url, prefix='process') + custom_tags
        try:
            r = self.http.get(url)
            r.raise_for_status()
        except Exception:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags)
            raise
        else:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)

# TODO: move to utils
@staticmethod
def tags_from_url(url, prefix=None):
    if prefix:
        prefix = prefix + '_'
    parsed_url = urlparse(url)
    gitlab_host = parsed_url.hostname
    gitlab_port = 443 if parsed_url.scheme == 'https' else (parsed_url.port or 80)
    return [
        '{}host:{}'.format(prefix, gitlab_host),
        '{}port:{}'.format(prefix, gitlab_port),
    ]

# TAGS:
#   - druid service name e.g. druid/broker

# TODO: Handle version
# etcd.server.version,gauge,,item,,Which version is running. 1 for 'server_version' label with current version.,0,etcd,
