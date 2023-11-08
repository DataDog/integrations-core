# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, List  # noqa: F401

import yaml
from six.moves import xmlrpc_client as xmlrpclib

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.ddyaml import yaml_load_force_loader

from .metrics import build_metric


class CitrixHypervisorCheck(AgentCheck):
    __NAMESPACE__ = 'citrix_hypervisor'
    SERVICE_CHECK_CONNECT = 'can_connect'

    def __init__(self, name, init_config, instances):
        # type: (str, Dict, List[Dict]) -> None
        super(CitrixHypervisorCheck, self).__init__(name, init_config, instances)

        self._last_timestamp = 0

        if self.instance.get('url') is None:
            raise ConfigurationError('Missing configuration option: url')
        self._base_url = self.instance['url'].rstrip('/')

        self.tags = self.instance.get('tags', [])
        self.xenserver = None  # type: Any
        self._additional_tags = []  # type: List[str]

        self.check_initializations.append(self._check_connection)

    def _check_connection(self):
        # type: () -> None
        # Get the latest timestamp to reduce the length of the update endpoint response
        r = self.http.get(self._base_url + '/host_rrd', params={'json': 'true'})
        if r.status_code == 200:
            self._last_timestamp = int(float(r.json()['lastupdate'])) - 60
        else:
            self.log.warning("Couldn't initialize the timestamp due to HTTP error %s, set it to 0", r.reason)

    def _get_updated_metrics(self):
        # type: () -> Dict
        params = {
            'start': self._last_timestamp,
            'host': 'true',
            'json': 'true',
        }
        r = self.http.get(self._base_url + '/rrd_updates', params=params)
        r.raise_for_status()
        # Response is not formatted for simplejson, it's missing double quotes " around the field names
        # Explicitly use the python safe loader, the C binding is failing
        # See https://github.com/yaml/pyyaml/issues/443
        data = yaml_load_force_loader(r.content, Loader=yaml.SafeLoader)

        if data['meta'].get('end') is not None:
            self._last_timestamp = int(data['meta']['end'])
        else:
            for key in data['meta'].keys():
                if data['meta'][key] is None and key.startswith('end'):
                    self._last_timestamp = int(key.split(':')[-1])

        return data

    def submit_metrics(self, data):
        # type: (Dict) -> None
        legends = data['meta']['legend']
        values = data['data'][0]['values']
        for i in range(len(legends)):
            metric_name, tags = build_metric(legends[i], self.log)

            if metric_name is not None:
                self.gauge(metric_name, values[i], tags=self.tags + self._additional_tags + tags)

    def _session_login(self, server):
        # type: (Any) -> Dict[str, str]
        try:
            session = server.session.login_with_password(
                self.instance.get('username', ''), self.instance.get('password', '')
            )
            return session
        except Exception as e:
            self.log.warning(e)
        return {}

    def _get_master_session(self, session):
        # type: (Dict[str, str]) -> Dict[str, str]
        # {'Status': 'Failure', 'ErrorDescription': ['HOST_IS_SLAVE', '192.168.101.102']}
        if len(session.get('ErrorDescription', [])) < 1:
            return {}

        master_address = session['ErrorDescription'][1]
        if not master_address.startswith('http://'):
            master_address = 'http://' + master_address
        master_xenserver = xmlrpclib.Server(master_address)

        # Master credentials can be different, we could specify new `master_username` and
        # `master_password` options later if requested
        master_session = self._session_login(master_xenserver)

        if master_session.get('Status') == 'Success':
            self.xenserver = master_xenserver
            return master_session

        return {}

    def open_session(self):
        # type: () -> Dict[str, str]
        try:
            self.xenserver = xmlrpclib.Server(self._base_url)
        except Exception as e:
            self.log.warning(str(e))
            return {}

        # See reference https://xapi-project.github.io/xen-api/classes/session.html
        session = self._session_login(self.xenserver)

        if session.get('Status') == 'Failure':
            if 'SESSION_AUTHENTICATION_FAILED' in session.get('ErrorDescription', []):
                self.log.warning('Connection failed with xmlrpc: %s', str(session['ErrorDescription']))
                return {}
            if 'HOST_IS_SLAVE' in session.get('ErrorDescription', []):
                # If xenserver host is a slave, open a connection with the pool master
                # {'Status': 'Failure', 'ErrorDescription': ['HOST_IS_SLAVE', '192.168.101.102']}
                self.log.debug('Host is a slave, trying to connect to the pool master')
                self._additional_tags.append('server_type:slave')
                return self._get_master_session(session)

            self.log.warning('Unknown xmlrpc error: %s', str(session))
            return {}
        elif session.get('Status') == 'Success':
            self._additional_tags.append('server_type:master')

            return session
        return {}

    def check(self, _):
        # type: (Any) -> None
        self._additional_tags = []
        session = self.open_session()
        if session.get('Value'):
            ref = session['Value']
            self._collect_version(ref)
            self.xenserver.session.logout(ref)

        try:
            data = self._get_updated_metrics()

            self.service_check(
                self.SERVICE_CHECK_CONNECT,
                self.OK,
                ['citrix_hypervisor_url:{}'.format(self._base_url)] + self._additional_tags + self.tags,
            )
        except Exception as e:
            self.service_check(
                self.SERVICE_CHECK_CONNECT,
                self.CRITICAL,
                ['citrix_hypervisor_url:{}'.format(self._base_url)] + self._additional_tags + self.tags,
            )
            self.log.exception(e)
        else:
            self.submit_metrics(data)

    @AgentCheck.metadata_entrypoint
    def _collect_version(self, sessionref):
        # type: (str) -> None
        """
        In a pool, Citrix Hypervisors must have the same product version, so the version
        of the master hypervisors is also the version of the current hypervisor.
        https://docs.citrix.com/en-us/xencenter/current-release/pools-requirements.html
        """
        try:
            host = self.xenserver.session.get_this_host(sessionref, sessionref)
            if host.get('Status') != 'Success':
                self.log.warning('get_this_host call failed: %s', str(host))

            software_version = self.xenserver.host.get_software_version(sessionref, host['Value'])
            if software_version.get('Status') != 'Success':
                self.log.warning('get_software_version call failed: %s', str(software_version))

            product_version = software_version['Value'].get('product_version')
            if product_version:
                self.set_metadata('version', product_version)
        except Exception as e:
            self.log.warning("Couldn't get product version: %s", str(e))
