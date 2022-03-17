# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import is_affirmative


class TeradataConfig(object):
    def __init__(self, instance):
        self.server = instance.get('server')
        self.port = int(instance.get('port', 1025))
        self.account = instance.get('account')
        self.username = instance.get('username')
        self.password = instance.get('password')
        self.db = instance.get('database')
        self.collect_res_usage = is_affirmative(instance.get('collect_res_usage'))
        self.use_tls = is_affirmative(instance.get('use_tls', True))
        self.https_port = int(instance.get('https_port', 443))
        self.ssl_mode = instance.get('ssl_mode', 'PREFER')
        self.ssl_protocol = instance.get('ssl_protocol', 'TLSv1.2')
        self.ssl_ca = instance.get('ssl_ca')
        self.ssl_ca_path = instance.get('ssl_ca_path')
        self.auth_data = instance.get('auth_data')
        self.auth_mechanism = instance.get('auth_mechanism')
        self.tags = instance.get('tags', [])

    def get(self, option):
        return option
