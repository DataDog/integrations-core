# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import iteritems

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.config import _is_affirmative
from datadog_checks.base.utils.containers import hash_mutable

from . import aci_metrics
from .api import Api
from .capacity import Capacity
from .fabric import Fabric
from .tags import CiscoTags
from .tenant import Tenant

SOURCE_TYPE = 'cisco_aci'

SERVICE_CHECK_NAME = 'cisco_aci.can_connect'


class CiscoACICheck(AgentCheck):

    HTTP_CONFIG_REMAPPER = {'ssl_verify': {'name': 'tls_verify'}, 'pwd': {'name': 'password'}}

    def __init__(self, name, init_config, instances):
        super(CiscoACICheck, self).__init__(name, init_config, instances)
        self.tenant_metrics = aci_metrics.make_tenant_metrics()
        self.last_events_ts = {}
        self.external_host_tags = {}
        self._api_cache = {}
        self.check_tags = ['cisco']
        self.tagger = CiscoTags(log=self.log)

    def check(self, _):
        aci_url = self.instance.get('aci_url')
        aci_urls = self.instance.get('aci_urls', [])
        if aci_url:
            aci_urls.append(aci_url)

        if not aci_urls:
            raise ConfigurationError("The Cisco ACI check requires at least one url")

        username = self.instance['username']
        pwd = self.instance.get('pwd')
        instance_hash = hash_mutable(self.instance)

        appcenter = _is_affirmative(self.instance.get('appcenter'))

        cert_key = self.instance.get('cert_key')
        if not cert_key and self.instance.get('cert_key_path'):
            with open(self.instance.get('cert_key_path'), 'rb') as f:
                cert_key = f.read()

        cert_name = self.instance.get('cert_name')
        if not cert_name:
            cert_name = username

        cert_key_password = self.instance.get('cert_key_password')

        if instance_hash in self._api_cache:
            api = self._api_cache.get(instance_hash)
        else:
            api = Api(
                aci_urls,
                self.http,
                username,
                password=pwd,
                cert_name=cert_name,
                cert_key=cert_key,
                log=self.log,
                appcenter=appcenter,
                cert_key_password=cert_key_password,
            )
            self._api_cache[instance_hash] = api

        service_check_tags = []
        for url in aci_urls:
            service_check_tags.append("url:{}".format(url))
        service_check_tags.extend(self.check_tags)
        service_check_tags.extend(self.instance.get('tags', []))

        try:
            api.login()
        except Exception as e:
            self.log.error("Cannot login to the Cisco ACI: %s", e)
            self.service_check(
                SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message="aci login returned a status of {}".format(e),
                tags=service_check_tags,
            )
            raise

        self.tagger.api = api

        try:
            tenant = Tenant(self, api, self.instance, instance_hash)
            tenant.collect()
        except Exception as e:
            self.log.error('tenant collection failed: %s', e)
            self.service_check(
                SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message="aci tenant operations failed, returning a status of {}".format(e),
                tags=service_check_tags,
            )
            api.close()
            raise

        try:
            fabric = Fabric(self, api, self.instance)
            fabric.collect()
        except Exception as e:
            self.log.error('fabric collection failed: %s', e)
            self.service_check(
                SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message="aci fabric operations failed, returning a status of {}".format(e),
                tags=service_check_tags,
            )
            api.close()
            raise

        try:
            capacity = Capacity(api, self.instance, check_tags=self.check_tags, gauge=self.gauge, log=self.log)
            capacity.collect()
        except Exception as e:
            self.log.error('capacity collection failed: %s', e)
            self.service_check(
                SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message="aci capacity operations failed, returning a status of {}".format(e),
                tags=service_check_tags,
            )
            api.close()
            raise

        self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)

        self.set_external_tags(self.get_external_host_tags())

        api.close()

    def submit_metrics(self, metrics, tags, instance=None, obj_type="gauge", hostname=None):
        if instance is None:
            instance = {}

        user_tags = instance.get('tags', [])
        for mname, mval in iteritems(metrics):
            tags_to_send = []
            if mval:
                if hostname:
                    tags_to_send += self.check_tags
                tags_to_send += user_tags + tags
                if obj_type == "gauge":
                    self.gauge(mname, float(mval), tags=tags_to_send, hostname=hostname)
                elif obj_type == "rate":
                    self.rate(mname, float(mval), tags=tags_to_send, hostname=hostname)
                else:
                    log_line = "Trying to submit metric: %s with unknown type: %s"
                    self.log.debug(log_line, mname, obj_type)

    def get_external_host_tags(self):
        external_host_tags = []
        for hostname, tags in iteritems(self.external_host_tags):
            host_tags = tags + self.check_tags
            external_host_tags.append((hostname, {SOURCE_TYPE: host_tags}))
        return external_host_tags
