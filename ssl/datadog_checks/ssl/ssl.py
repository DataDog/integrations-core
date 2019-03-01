# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# to prevent conflicts with built-in SSL libraries
from __future__ import absolute_import
from datadog_checks.base import AgentCheck
from datadog_checks.errors import CheckException
# how to use http_check's utils.py for get_ca_certs_path code?
# from datadog_checks.base.utils import get_ca_certs_path
# not using this for anything yet:
# from datadog_checks.base import is_affirmative
import ssl
import socket

DEFAULT_EXPIRE_DAYS_WARNING = 14
DEFAULT_EXPIRE_DAYS_CRITICAL = 7
DEFAULT_EXPIRE_WARNING = DEFAULT_EXPIRE_DAYS_WARNING * 24 * 3600
DEFAULT_EXPIRE_CRITICAL = DEFAULT_EXPIRE_DAYS_CRITICAL * 24 * 3600


class SslCheck(AgentCheck):
    SERVICE_CHECK_CAN_CONNECT = 'ssl_cert.can_connect'
    SERVICE_CHECK_EXPIRATION = 'ssl_cert.expiration'

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        self.ca_certs = init_config.get('ca_certs')
        # if not self.ca_certs:
        # self.ca_certs = get_ca_certs_path()

    def check(self, instance):
        # ca_certs = self.ca_certs or instance.get('ca_certs')
        url = instance.get('url')
        # later get version from cert itself
        ssl_version = instance.get('ssl_version')
        tags = ['url:%s' % url, 'ssl_version:%s' % ssl_version]

        # It's a good idea to do some basic sanity checking. Try to be as
        # specific as possible, with the exceptions; you can fall back to
        # CheckException when in doubt though.
        if not url:  # or not search_string:
            raise CheckException("Configuration error, please fix ssl.yaml")

        try:
            context = ssl.create_default_context()
            with socket.create_connection((url, 443)) as sock:
                with context.wrap_socket(sock, server_hostname=url) as ssl_sock:
                    print(ssl_sock.getpeercert())
                    print(ssl_sock.version())
            # r = requests.get(url)
            # r.raise_for_status()
            # if search_string in r.text:
            #     # Page is accessible and the string is present.
            #     self.service_check('ssl.all_good', self.OK)
            # else:
            #     # Page is accessible but the string was not found.
            #     self.service_check('ssl.all_good', self.WARNING)
        except Exception:  # as e:
            # Something went horribly wrong. Ideally we'd be more specific...
            # print("Exception: "+e)
            self.service_check('ssl_cert.can_connect', self.CRITICAL, tags=tags)
