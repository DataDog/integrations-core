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
        self.cert_path = instance.get('local_cert_path')
        # We would tag by name parameter, IP/URL/hostname+port,
        # TLS version. If possible to protocols, tag by protocol.
        # Tags would be added to all the metrics and service checks.
        self.tags = [
            "name:{}".format(self.name)
        ] + self.custom_tags
        if not self.cert_path:
            self.tags = self.tags + ["host:{}".format(self.host),
                                     "port:{}".format(self.port)]

        self.cert_remote = True

        # check if remote/local
        if self.cert_path:
            print("getting local")
            self.cert_remote = False

        # self.get_config

    def check_properly_configured(self):
        return True
        # check if cert_remote is set
        # if not self.channel or not self.queue_manager_name or not self.host or not self.port:
        #     msg = "channel, queue_manager, host and port are all required configurations"
        #     raise ConfigurationError(msg)

        # costly since it would be executed every time
        # @property
        # def tags(self):
        #     return [
        #         "host:{}".format(self.host),
        #         "port:{}".format(self.port),
        #         "name:{}".format(self.name)
        #     ] + self.custom_tags
