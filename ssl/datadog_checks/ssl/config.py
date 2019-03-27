# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# from datadog_checks.config import is_affirmative

# compatability layer for agents under 6.6.0
try:
    from datadog_checks.errors import ConfigurationError
except ImportError:
    ConfigurationError = Exception


class SslConfig:
    """
    A config object. Parse the instance and return it as an object that can be passed around
    No need to parse the instance more than once in the check run
    """

    def __init__(self, instance):
        self.name = instance.get('name')
        self.host = instance.get('host')
        self.port = instance.get('port')
        self.host_and_port = "{}({})".format(self.host, self.port)
        self.timeout = instance.get('timeout')
        self.days_warning = instance.get('days_warning', '14')
        self.days_critical = instance.get('days_critical', '7')
        self.check_hostname = instance.get('check_hostname', 'true')
        self.ssl_hostname = instance.get('ssl_hostname')
        self.custom_tags = instance.get('tags', [])
        self.local_cert_path = instance.get('local_cert_path')
        # We would tag by name parameter, IP/URL/hostname+port,
        # TLS version. If possible to protocols, tag by protocol.
        # Tags would be added to all the metrics and service checks.
        self.tags = [
            "name:{}".format(self.name), "ssl_version:unknown"
        ] + self.custom_tags
        if not self.local_cert_path:
            self.tags = self.tags + ["host:{}".format(self.host),
                                     "port:{}".format(self.port)]

        self.cert_remote = True

        # check if remote/local
        if self.local_cert_path:
            print("getting local")
            self.cert_remote = False

        # self.get_config

    def check_properly_configured(self):
        if not self.local_cert_path and not self.host:
            msg = "Check must be configured with either a local certificate path or remote host."
            raise ConfigurationError(msg)
