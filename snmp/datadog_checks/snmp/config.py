# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import ipaddress
import time
import weakref
from collections import defaultdict
from logging import Logger, getLogger  # noqa: F401
from typing import Any, DefaultDict, Dict, Iterator, List, Optional, Set, Tuple  # noqa: F401

from datadog_checks.base import ConfigurationError, is_affirmative

from .mibs import MIBLoader
from .models import OID, Device
from .parsing import ParsedMetric, ParsedSymbolMetric, SymbolTag, parse_metrics, parse_symbol_metric_tags  # noqa: F401
from .pysnmp_types import (
    CommunityData,
    ContextData,
    OctetString,
    UsmUserData,
    hlapi,
    usmDESPrivProtocol,
    usmHMACMD5AuthProtocol,
)
from .resolver import OIDResolver
from .types import OIDMatch  # noqa: F401
from .utils import register_device_target

local_logger = getLogger(__name__)

SUPPORTED_DEVICE_TAGS = ['vendor']


class InstanceConfig:
    """Parse and hold configuration about a single instance."""

    DEFAULT_RETRIES = 5
    DEFAULT_TIMEOUT = 5
    DEFAULT_ALLOWED_FAILURES = 3
    DEFAULT_BULK_THRESHOLD = 0
    DEFAULT_WORKERS = 5
    DEFAULT_REFRESH_OIDS_CACHE_INTERVAL = 0  # `0` means disabled

    AUTH_PROTOCOL_MAPPING = {
        'md5': 'usmHMACMD5AuthProtocol',
        'sha': 'usmHMACSHAAuthProtocol',
        'sha224': 'usmHMAC128SHA224AuthProtocol',
        'sha256': 'usmHMAC192SHA256AuthProtocol',
        'sha384': 'usmHMAC256SHA384AuthProtocol',
        'sha512': 'usmHMAC384SHA512AuthProtocol',
    }

    PRIV_PROTOCOL_MAPPING = {
        'des': 'usmDESPrivProtocol',
        '3des': 'usm3DESEDEPrivProtocol',
        'aes': 'usmAesCfb128Protocol',
        'aes192': 'usmAesBlumenthalCfb192Protocol',
        'aes256': 'usmAesBlumenthalCfb256Protocol',
        'aes192c': 'usmAesCfb192Protocol',
        'aes256c': 'usmAesCfb256Protocol',
    }

    def __init__(
        self,
        instance,  # type: dict
        global_metrics=None,  # type: List[dict]
        mibs_path=None,  # type: str
        refresh_oids_cache_interval=DEFAULT_REFRESH_OIDS_CACHE_INTERVAL,  # type: int
        profiles=None,  # type: Dict[str, dict]
        profiles_by_oid=None,  # type: Dict[str, str]
        loader=None,  # type: MIBLoader
        logger=None,  # type: Logger
    ):
        # type: (...) -> None
        global_metrics = [] if global_metrics is None else global_metrics
        profiles = {} if profiles is None else profiles
        profiles_by_oid = {} if profiles_by_oid is None else profiles_by_oid
        loader = MIBLoader() if loader is None else loader

        # Clean empty or null values. This will help templating.
        for key, value in list(instance.items()):
            if value in (None, ""):
                instance.pop(key)

        self.logger = weakref.ref(local_logger) if logger is None else weakref.ref(logger)

        self.instance = instance
        self.tags = instance.get('tags', [])
        self.metrics = instance.get('metrics', [])
        metric_tags = instance.get('metric_tags', [])

        profile = instance.get('profile')

        if is_affirmative(instance.get('use_global_metrics', True)):
            self.metrics.extend(global_metrics)

        self.enforce_constraints = is_affirmative(instance.get('enforce_mib_constraints', True))
        self._snmp_engine = loader.create_snmp_engine(mibs_path)
        mib_view_controller = loader.get_mib_view_controller(mibs_path)
        self._resolver = OIDResolver(mib_view_controller, self.enforce_constraints)

        self.device = None  # type: Optional[Device]
        self.ip_network = None

        self.discovered_instances = {}  # type: Dict[str, InstanceConfig]
        self.failing_instances = defaultdict(int)  # type: DefaultDict[str, int]
        self.allowed_failures = int(instance.get('discovery_allowed_failures', self.DEFAULT_ALLOWED_FAILURES))
        self.workers = int(instance.get('workers', self.DEFAULT_WORKERS))

        self.bulk_threshold = int(instance.get('bulk_threshold', self.DEFAULT_BULK_THRESHOLD))

        self._auth_data = self.get_auth_data(instance)
        self._context_data = ContextData(*self.get_context_data(instance))

        timeout = int(instance.get('timeout', self.DEFAULT_TIMEOUT))
        retries = int(instance.get('retries', self.DEFAULT_RETRIES))

        ip_address = instance.get('ip_address')
        network_address = instance.get('network_address')

        if not ip_address and not network_address:
            raise ConfigurationError('An IP address or a network address needs to be specified')

        if ip_address and network_address:
            raise ConfigurationError('Only one of IP address and network address must be specified')

        if ip_address:
            port = int(instance.get('port', 161))

            target = register_device_target(
                ip_address,
                port,
                timeout=timeout,
                retries=retries,
                engine=self._snmp_engine,
                auth_data=self._auth_data,
                context_data=self._context_data,
            )
            device = Device(ip=ip_address, port=port, target=target)
            self.device = device
            self.tags.extend(device.tags)

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

        scalar_oids, next_oids, bulk_oids, self.parsed_metrics = self.parse_metrics(self.metrics)
        tag_oids, self.parsed_metric_tags = self.parse_metric_tags(metric_tags)
        if tag_oids:
            scalar_oids.extend(tag_oids)

        refresh_interval_sec = instance.get('refresh_oids_cache_interval', refresh_oids_cache_interval)
        self.oid_config = OIDConfig(refresh_interval_sec)
        self.oid_config.add_parsed_oids(scalar_oids=scalar_oids, next_oids=next_oids, bulk_oids=bulk_oids)

        if profile:
            if profile not in profiles:
                raise ConfigurationError("Unknown profile '{}'".format(profile))
            self.refresh_with_profile(profiles[profile])
            self.add_profile_tag(profile)

        self._uptime_metric_added = False

    def resolve_oid(self, oid):
        # type: (OID) -> OIDMatch
        return self._resolver.resolve_oid(oid)

    def refresh_with_profile(self, profile):
        # type: (Dict[str, Any]) -> None
        metrics = profile['definition'].get('metrics', [])
        scalar_oids, next_oids, bulk_oids, parsed_metrics = self.parse_metrics(metrics)

        metric_tags = profile['definition'].get('metric_tags', [])
        tag_oids, parsed_metric_tags = self.parse_metric_tags(metric_tags)

        device = profile['definition'].get('device', {})
        self.add_device_tags(device)

        # NOTE: `profile` may contain metrics and metric tags that have already been ingested in this configuration.
        # As a result, multiple copies of metrics/tags will be fetched and submitted to Datadog, which is inefficient
        # and possibly problematic.
        # In the future we'll probably want to implement de-duplication.

        self.metrics.extend(metrics)
        self.oid_config.add_parsed_oids(scalar_oids=scalar_oids + tag_oids, next_oids=next_oids, bulk_oids=bulk_oids)
        self.parsed_metrics.extend(parsed_metrics)
        self.parsed_metric_tags.extend(parsed_metric_tags)

    def add_profile_tag(self, profile_name):
        # type: (str) -> None
        self.tags.append('snmp_profile:{}'.format(profile_name))

    def add_device_tags(self, device):
        # type: (dict) -> None
        for device_tag in SUPPORTED_DEVICE_TAGS:
            tag = device.get(device_tag)
            if tag:
                self.tags.append('device_{}:{}'.format(device_tag, tag))

    @classmethod
    def get_auth_data(cls, instance):
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
                protocol_name = instance['authProtocol']
                if protocol_name.lower() in cls.AUTH_PROTOCOL_MAPPING:
                    protocol_name = cls.AUTH_PROTOCOL_MAPPING[protocol_name.lower()]
                auth_protocol = getattr(hlapi, protocol_name)

            if 'privProtocol' in instance:
                protocol_name = instance['privProtocol']
                if protocol_name.lower() in cls.PRIV_PROTOCOL_MAPPING:
                    protocol_name = cls.PRIV_PROTOCOL_MAPPING[protocol_name.lower()]
                priv_protocol = getattr(hlapi, protocol_name)

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
        # type: (list) -> Tuple[List[OID], List[OID], List[OID], List[ParsedMetric]]
        """Parse configuration and returns data to be used for SNMP queries."""
        # Use bulk for SNMP version > 1 only.
        bulk_threshold = self.bulk_threshold if self._auth_data.mpModel else 0
        result = parse_metrics(metrics, resolver=self._resolver, logger=self.logger(), bulk_threshold=bulk_threshold)
        return result['oids'], result['next_oids'], result['bulk_oids'], result['parsed_metrics']

    def parse_metric_tags(self, metric_tags):
        # type: (list) -> Tuple[List[OID], List[SymbolTag]]
        """Parse configuration for global metric_tags."""
        result = parse_symbol_metric_tags(metric_tags, resolver=self._resolver)
        return result['oids'], result['parsed_symbol_tags']

    def add_uptime_metric(self):
        # type: () -> None
        if self._uptime_metric_added:
            return
        # Reference sysUpTimeInstance directly, see http://oidref.com/1.3.6.1.2.1.1.3.0
        uptime_oid = OID('1.3.6.1.2.1.1.3.0')
        self.oid_config.add_parsed_oids(scalar_oids=[uptime_oid])
        self._resolver.register(uptime_oid, 'sysUpTimeInstance')

        parsed_metric = ParsedSymbolMetric('sysUpTimeInstance', forced_type='gauge')
        self.parsed_metrics.append(parsed_metric)
        self._uptime_metric_added = True


class OIDConfig(object):
    """
    Manages scalar/next/bulk oids to be used for snmp PDU calls.
    """

    def __init__(self, refresh_interval_sec):
        # type: (bool) -> None
        self._refresh_interval_sec = refresh_interval_sec
        self._last_ts = 0  # type: float

        self._scalar_oids = []  # type: List[OID]
        self._next_oids = []  # type: List[OID]
        self._bulk_oids = []  # type: List[OID]

        self._all_scalar_oids = []  # type: List[OID]
        self._use_scalar_oids_cache = False

    @property
    def scalar_oids(self):
        # type: () -> List[OID]
        if self._use_scalar_oids_cache:
            return self._all_scalar_oids
        return self._scalar_oids

    @property
    def next_oids(self):
        # type: () -> List[OID]
        if self._use_scalar_oids_cache:
            return []
        return self._next_oids

    @property
    def bulk_oids(self):
        # type: () -> List[OID]
        if self._use_scalar_oids_cache:
            return []
        return self._bulk_oids

    def add_parsed_oids(self, scalar_oids=None, next_oids=None, bulk_oids=None):
        # type: (List[OID], List[OID], List[OID]) -> None
        if scalar_oids:
            self._scalar_oids.extend(scalar_oids)
        if next_oids:
            self._next_oids.extend(next_oids)
        if bulk_oids:
            self._bulk_oids.extend(bulk_oids)
        self.reset()

    def has_oids(self):
        # type: () -> bool
        """
        Return whether there are OIDs to fetch.
        """
        return bool(self.scalar_oids or self.next_oids or self.bulk_oids)

    def _is_cache_enabled(self):
        # type: () -> bool
        return self._refresh_interval_sec > 0

    def update_scalar_oids(self, new_scalar_oids):
        # type: (List[OID]) -> None
        """
        Use only scalar oids for following snmp calls.
        """
        if not self._is_cache_enabled():
            return
        # Do not update if we are already using scalar oids cache.
        if self._use_scalar_oids_cache:
            return
        self._all_scalar_oids = new_scalar_oids
        self._use_scalar_oids_cache = True
        self._last_ts = time.time()

    def should_reset(self):
        # type: () -> bool
        """
        Whether we should reset OIDs to initial parsed OIDs.
        """
        if not self._is_cache_enabled():
            return False
        elapsed = time.time() - self._last_ts
        return elapsed > self._refresh_interval_sec

    def reset(self):
        # type: () -> None
        """
        Reset scalar oids cache.
        """
        self._all_scalar_oids = []
        self._use_scalar_oids_cache = False
