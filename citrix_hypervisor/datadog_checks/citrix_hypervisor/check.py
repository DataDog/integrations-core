# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree

from six.moves import xmlrpc_client as xmlrpclib

from datadog_checks.base import AgentCheck, ConfigurationError, to_native_string

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
        # type: () -> Tuple[Optional[ElementTree.Element], Optional[ElementTree.Element]]
        params = {
            'start': self._last_timestamp,
            'host': 'true',
        }
        r = self.http.get(self._base_url + '/rrd_updates', params=params)
        r.raise_for_status()
        # Response is not formatted for simplejson, it's missing double quotes " around the field names
        content = to_native_string(r.content).replace('\\n', '')
        data = ElementTree.fromstring(content)

        meta = data.find('meta')
        if meta is None:
            return None, None
        last_timestamp = meta.find('end')
        if last_timestamp is not None:
            self._last_timestamp = int(to_native_string(last_timestamp.text))

        values = data.find('data')
        if values is None:
            return None, None

        # The first row is the latest one
        return meta.find('legend'), values.find('row')

    def submit_metrics(self, legends, values):
        # type: (ElementTree.Element, ElementTree.Element) -> None

        # First entry of values is the timestamp
        if len(legends) != len(values) - 1:
            return

        for i in range(len(legends)):
            metric_name, tags = build_metric(to_native_string(legends[i].text), self.log)

            if metric_name is not None:
                self.gauge(
                    metric_name,
                    float(to_native_string(values[i + 1].text)),
                    tags=self.tags + self._additional_tags + tags,
                )

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
        master_address = session['ErrorDescription'][1]
        if not master_address.startswith('http://'):
            master_address = 'http://' + master_address
        master_xenserver = xmlrpclib.Server(master_address)

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

        self._additional_tags.append('server_type:master')

        return session

    def check(self, _):
        # type: (Any) -> None
        self._additional_tags = []
        session = self.open_session()
        if session.get('Value'):
            ref = session['Value']
            self._collect_version(ref)
            self.xenserver.session.logout(ref)

        try:
            legends, values = self._get_updated_metrics()

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
            if legends is not None and values is not None:
                self.submit_metrics(legends, values)

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
