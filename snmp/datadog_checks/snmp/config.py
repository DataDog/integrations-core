# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import ipaddress
from collections import defaultdict
from typing import Any, DefaultDict, Dict, Iterator, List, Optional, Set, Tuple

from datadog_checks.base import ConfigurationError, is_affirmative

from .models import OID
from .parsing import ParsedMetric, ParsedMetricTag, ParsedSymbolMetric, parse_metric_tags, parse_metrics
from .pysnmp_types import (
    CommunityData,
    ContextData,
    DirMibSource,
    MibViewController,
    OctetString,
    SnmpEngine,
    UdpTransportTarget,
    UsmUserData,
    hlapi,
    lcd,
    usmDESPrivProtocol,
    usmHMACMD5AuthProtocol,
)
from .resolver import OIDResolver
from .types import OIDMatch


class InstanceConfig:
    """Parse and hold configuration about a single instance."""

    DEFAULT_RETRIES = 5
    DEFAULT_TIMEOUT = 5
    DEFAULT_ALLOWED_FAILURES = 3
    DEFAULT_BULK_THRESHOLD = 0
    DEFAULT_WORKERS = 5

    def __init__(
        self,
        instance,  # type: dict
        global_metrics=None,  # type: List[dict]
        mibs_path=None,  # type: str
        profiles=None,  # type: Dict[str, dict]
        profiles_by_oid=None,  # type: Dict[str, str]
    ):
        # type: (...) -> None
        global_metrics = [] if global_metrics is None else global_metrics
        profiles = {} if profiles is None else profiles
        profiles_by_oid = {} if profiles_by_oid is None else profiles_by_oid

        # Clean empty or null values. This will help templating.
        for key, value in list(instance.items()):
            if value in (None, ""):
                instance.pop(key)

        self.instance = instance
        self.tags = instance.get('tags', [])
        self.metrics = instance.get('metrics', [])
        metric_tags = instance.get('metric_tags', [])

        profile = instance.get('profile')

        if is_affirmative(instance.get('use_global_metrics', True)):
            self.metrics.extend(global_metrics)

        self.enforce_constraints = is_affirmative(instance.get('enforce_mib_constraints', True))
        self._snmp_engine, mib_view_controller = self.create_snmp_engine(mibs_path)
        self._resolver = OIDResolver(mib_view_controller, self.enforce_constraints)

        self.ip_address = None
        self.ip_network = None

        self.discovered_instances = {}  # type: Dict[str, InstanceConfig]
        self.failing_instances = defaultdict(int)  # type: DefaultDict[str, int]
        self.allowed_failures = int(instance.get('discovery_allowed_failures', self.DEFAULT_ALLOWED_FAILURES))
        self.workers = int(instance.get('workers', self.DEFAULT_WORKERS))

        self.bulk_threshold = int(instance.get('bulk_threshold', self.DEFAULT_BULK_THRESHOLD))

        timeout = int(instance.get('timeout', self.DEFAULT_TIMEOUT))
        retries = int(instance.get('retries', self.DEFAULT_RETRIES))

        ip_address = instance.get('ip_address')
        network_address = instance.get('network_address')

        if not ip_address and not network_address:
            raise ConfigurationError('An IP address or a network address needs to be specified')

        if ip_address and network_address:
            raise ConfigurationError('Only one of IP address and network address must be specified')

        if ip_address:
            self._transport = self.get_transport_target(instance, timeout, retries)

            self.ip_address = ip_address
            self.tags.append('snmp_device:{}'.format(self.ip_address))

        if network_address:
            if isinstance(network_address, bytes):
                network_address = network_address.decode('utf-8')
            self.ip_network = ipaddress.ip_network(network_address)

        ignored_ip_addresses = instance.get('ignored_ip_addresses', [])

        if not isinstance(ignored_ip_addresses, list):
            raise ConfigurationError(
                'ignored_ip_addresses should be a list (got {})'.format(type(ignored_ip_addresses))
            )

        self.ignored_ip_addresses = set(ignored_ip_addresses)  # type: Set[str]

        if not self.metrics and not profiles_by_oid and not profile:
            raise ConfigurationError('Instance should specify at least one metric or profiles should be defined')

        self._auth_data = self.get_auth_data(instance)

        self.all_oids, self.bulk_oids, self.parsed_metrics = self.parse_metrics(self.metrics)
        tag_oids, self.parsed_metric_tags = self.parse_metric_tags(metric_tags)
        if tag_oids:
            self.all_oids.extend(tag_oids)

        if profile:
            if profile not in profiles:
                raise ConfigurationError("Unknown profile '{}'".format(profile))
            self.refresh_with_profile(profiles[profile])
            self.add_profile_tag(profile)

        self._context_data = ContextData(*self.get_context_data(instance))

        self._uptime_metric_added = False

        if ip_address:
            self._addr_name, _ = lcd.configure(
                self._snmp_engine, self._auth_data, self._transport, self._context_data.contextName
            )

    def resolve_oid(self, oid):
        # type: (OID) -> OIDMatch
        return self._resolver.resolve_oid(oid)

    def refresh_with_profile(self, profile):
        # type: (Dict[str, Any]) -> None
        metrics = profile['definition'].get('metrics', [])
        all_oids, bulk_oids, parsed_metrics = self.parse_metrics(metrics)

        metric_tags = profile['definition'].get('metric_tags', [])
        tag_oids, parsed_metric_tags = self.parse_metric_tags(metric_tags)

        # NOTE: `profile` may contain metrics and metric tags that have already been ingested in this configuration.
        # As a result, multiple copies of metrics/tags will be fetched and submitted to Datadog, which is inefficient
        # and possibly problematic.
        # In the future we'll probably want to implement de-duplication.

        self.metrics.extend(metrics)
        self.all_oids.extend(all_oids)
        self.bulk_oids.extend(bulk_oids)
        self.parsed_metrics.extend(parsed_metrics)
        self.parsed_metric_tags.extend(parsed_metric_tags)
        self.all_oids.extend(tag_oids)

    def add_profile_tag(self, profile_name):
        # type: (str) -> None
        self.tags.append('snmp_profile:{}'.format(profile_name))

    @staticmethod
    def create_snmp_engine(mibs_path=None):
        # type: (str) -> Tuple[SnmpEngine, MibViewController]
        """
        Create a command generator to perform all the snmp query.
        If mibs_path is not None, load the mibs present in the custom mibs
        folder. (Need to be in pysnmp format)
        """
        snmp_engine = SnmpEngine()
        mib_builder = snmp_engine.getMibBuilder()

        if mibs_path is not None:
            mib_builder.addMibSources(DirMibSource(mibs_path))

        mib_view_controller = MibViewController(mib_builder)

        return snmp_engine, mib_view_controller

    @staticmethod
    def get_transport_target(instance, timeout, retries):
        # type: (Dict[str, Any], float, int) -> Any
        """
        Generate a Transport target object based on the instance's configuration
        """
        ip_address = instance['ip_address']
        port = int(instance.get('port', 161))  # Default SNMP port
        return UdpTransportTarget((ip_address, port), timeout=timeout, retries=retries)

    @staticmethod
    def get_auth_data(instance):
        # type: (Dict[str, Any]) -> Any
        """
        Generate a Security Parameters object based on the instance's
        configuration.
        """
        if 'community_string' in instance:
            # SNMP v1 - SNMP v2
            # See http://snmplabs.com/pysnmp/docs/api-reference.html#pysnmp.hlapi.CommunityData
            if int(instance.get('snmp_version', 2)) == 1:
                return CommunityData(instance['community_string'], mpModel=0)
            return CommunityData(instance['community_string'], mpModel=1)

        if 'user' in instance:
            # SNMP v3
            user = instance['user']
            auth_key = None
            priv_key = None
            auth_protocol = None
            priv_protocol = None

            if 'authKey' in instance:
                auth_key = instance['authKey']
                auth_protocol = usmHMACMD5AuthProtocol

            if 'privKey' in instance:
                priv_key = instance['privKey']
                auth_protocol = usmHMACMD5AuthProtocol
                priv_protocol = usmDESPrivProtocol

            if 'authProtocol' in instance:
                auth_protocol = getattr(hlapi, instance['authProtocol'])

            if 'privProtocol' in instance:
                priv_protocol = getattr(hlapi, instance['privProtocol'])

            return UsmUserData(user, auth_key, priv_key, auth_protocol, priv_protocol)

        raise ConfigurationError('An authentication method needs to be provided')

    @staticmethod
    def get_context_data(instance):
        # type: (Dict[str, Any]) -> Tuple[Optional[OctetString], str]
        """
        Generate a Context Parameters object based on the instance's
        configuration.
        We do not use the hlapi currently, but the rfc3413.oneliner.cmdgen
        accepts Context Engine Id (always None for now) and Context Name parameters.
        """
        context_engine_id = None
        context_name = ''

        if 'user' in instance:
            if 'context_engine_id' in instance:
                context_engine_id = OctetString(instance['context_engine_id'])

            if 'context_name' in instance:
                context_name = instance['context_name']

        return context_engine_id, context_name

    def network_hosts(self):
        # type: () -> Iterator[str]
        if self.ip_network is None:
            raise RuntimeError('Expected ip_network to be set to iterate over network hosts.')

        for ip_address in self.ip_network.hosts():
            host = str(ip_address)

            if host in self.discovered_instances:
                continue

            if host in self.ignored_ip_addresses:
                continue

            yield host

    def parse_metrics(self, metrics):
        # type: (list) -> Tuple[List[OID], List[OID], List[ParsedMetric]]
        """Parse configuration and returns data to be used for SNMP queries."""
        # Use bulk for SNMP version > 1 only.
        bulk_threshold = self.bulk_threshold if self._auth_data.mpModel else 0
        result = parse_metrics(metrics, resolver=self._resolver, bulk_threshold=bulk_threshold)
        return result['oids'], result['bulk_oids'], result['parsed_metrics']

    def parse_metric_tags(self, metric_tags):
        # type: (list) -> Tuple[List[OID], List[ParsedMetricTag]]
        """Parse configuration for global metric_tags."""
        result = parse_metric_tags(metric_tags, resolver=self._resolver)
        return result['oids'], result['parsed_metric_tags']

    def add_uptime_metric(self):
        # type: () -> None
        if self._uptime_metric_added:
            return
        # Reference sysUpTimeInstance directly, see http://oidref.com/1.3.6.1.2.1.1.3.0
        uptime_oid = OID('1.3.6.1.2.1.1.3.0')
        self.all_oids.append(uptime_oid)
        self._resolver.register(uptime_oid, 'sysUpTimeInstance')

        parsed_metric = ParsedSymbolMetric('sysUpTimeInstance', forced_type='gauge')
        self.parsed_metrics.append(parsed_metric)
        self._uptime_metric_added = True
