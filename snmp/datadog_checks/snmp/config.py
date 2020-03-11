# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import ipaddress
from collections import defaultdict
from typing import Any, Callable, DefaultDict, Dict, Iterator, List, Optional, Set, Tuple, Union

from datadog_checks.base import ConfigurationError, is_affirmative

from .models import OID
from .pysnmp_types import (
    CommunityData,
    ContextData,
    DirMibSource,
    MibViewController,
    ObjectIdentity,
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


class ParsedMetric(object):

    __slots__ = ('name', 'metric_tags', 'forced_type', 'enforce_scalar')

    def __init__(self, name, metric_tags, forced_type, enforce_scalar=True):  # type: ignore
        self.name = name
        self.metric_tags = metric_tags
        self.forced_type = forced_type
        self.enforce_scalar = enforce_scalar


class ParsedTableMetric(object):

    __slots__ = ('name', 'index_tags', 'column_tags', 'forced_type')

    def __init__(
        self,
        name,  # type: str
        index_tags,  # type: List[Tuple[str, int]]
        column_tags,  # type: List[Tuple[str, str]]
        forced_type=None,  # type: str
    ):
        # type: (...) -> None
        self.name = name
        self.index_tags = index_tags
        self.column_tags = column_tags
        self.forced_type = forced_type


class ParsedMetricTag(object):

    __slots__ = ('name', 'symbol')

    def __init__(self, name, symbol):
        # type: (str, str) -> None
        self.name = name
        self.symbol = symbol


def _no_op(*args, **kwargs):
    # type: (*Any, **Any) -> None
    """
    A 'do-nothing' replacement for the `warning()` AgentCheck function, suitable for when those
    functions are not available (e.g. in unit tests).
    """


class InstanceConfig:
    """Parse and hold configuration about a single instance."""

    DEFAULT_RETRIES = 5
    DEFAULT_TIMEOUT = 1
    DEFAULT_ALLOWED_FAILURES = 3
    DEFAULT_BULK_THRESHOLD = 0
    DEFAULT_WORKERS = 5

    def __init__(
        self,
        instance,  # type: dict
        warning=_no_op,  # type: Callable[..., None]
        global_metrics=None,  # type: List[dict]
        mibs_path=None,  # type: str
        profiles=None,  # type: Dict[str, dict]
        profiles_by_oid=None,  # type: Dict[str, str]
    ):
        # type: (...) -> None
        global_metrics = [] if global_metrics is None else global_metrics
        profiles = {} if profiles is None else profiles
        profiles_by_oid = {} if profiles_by_oid is None else profiles_by_oid

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

        self.all_oids, self.bulk_oids, self.parsed_metrics = self.parse_metrics(self.metrics, warning)
        tag_oids, self.parsed_metric_tags = self.parse_metric_tags(metric_tags)
        if tag_oids:
            self.all_oids.extend(tag_oids)

        if profile:
            if profile not in profiles:
                raise ConfigurationError("Unknown profile '{}'".format(profile))
            self.refresh_with_profile(profiles[profile], warning)
            self.add_profile_tag(profile)

        self._context_data = ContextData(*self.get_context_data(instance))

        self._uptime_metric_added = False

        if ip_address:
            self._addr_name, _ = lcd.configure(
                self._snmp_engine, self._auth_data, self._transport, self._context_data.contextName
            )

    def resolve_oid(self, oid):
        # type: (OID) -> Tuple[str, Tuple[str, ...]]
        return self._resolver.resolve_oid(oid)

    def refresh_with_profile(self, profile, warning):
        # type: (Dict[str, Any], Callable[..., None]) -> None
        metrics = profile['definition'].get('metrics', [])
        all_oids, bulk_oids, parsed_metrics = self.parse_metrics(metrics, warning)

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

    def parse_metrics(
        self,
        metrics,  # type: List[Dict[str, Any]]
        warning,  # type: Callable[..., None]
    ):
        # type: (...) -> Tuple[List[OID], List[OID], List[Union[ParsedMetric, ParsedTableMetric]]]
        """Parse configuration and returns data to be used for SNMP queries.

        `oids` is a dictionnary of SNMP tables to symbols to query.
        """
        table_oids = {}  # type: Dict[Tuple[str, str], Tuple[OID, List[OID]]]
        parsed_metrics = []  # type: List[Union[ParsedMetric, ParsedTableMetric]]

        def extract_symbol(mib, symbol):
            # type: (str, Union[str, Dict[str, str]]) -> Tuple[OID, str]
            if isinstance(symbol, dict):
                oid = OID(symbol['OID'])
                symbol_name = symbol['name']
                self._resolver.register(oid, symbol_name)
            else:
                oid = OID(ObjectIdentity(mib, symbol))
                symbol_name = symbol

            return oid, symbol_name

        def get_table_symbols(mib, table_def):
            # type: (str, Dict[str, str]) -> Tuple[List[OID], str]
            table_oid, table = extract_symbol(mib, table_def)
            key = (mib, table)

            if key in table_oids:
                return table_oids[key][1], table

            symbols = []  # type: List[OID]

            table_oids[key] = (table_oid, symbols)

            return symbols, table

        # Check the metrics completely defined
        for metric in metrics:
            forced_type = metric.get('forced_type')
            metric_tags = metric.get('metric_tags', [])

            if 'MIB' in metric:
                if not ('table' in metric or 'symbol' in metric):
                    raise ConfigurationError('When specifying a MIB, you must specify either table or symbol')

                if 'symbol' in metric:
                    to_query = metric['symbol']

                    try:
                        _, parsed_metric_name = get_table_symbols(metric['MIB'], to_query)
                    except Exception as e:
                        warning("(1) Can't generate MIB object for variable : %s\nException: %s", metric, e)
                    else:
                        parsed_metric = ParsedMetric(parsed_metric_name, metric_tags, forced_type)
                        parsed_metrics.append(parsed_metric)

                    continue

                elif 'symbols' not in metric:
                    raise ConfigurationError('When specifying a table, you must specify a list of symbols')

                symbols, _ = get_table_symbols(metric['MIB'], metric['table'])
                index_tags = []
                column_tags = []

                for metric_tag in metric_tags:
                    if not ('tag' in metric_tag and ('index' in metric_tag or 'column' in metric_tag)):
                        raise ConfigurationError(
                            'When specifying metric tags, you must specify a tag, and an index or column'
                        )

                    tag_key = metric_tag['tag']

                    if 'column' in metric_tag:
                        # In case it's a column, we need to query it as well
                        mib = metric_tag.get('MIB', metric['MIB'])
                        oid, column = extract_symbol(mib, metric_tag['column'])
                        column_tags.append((tag_key, column))

                        if 'table' in metric_tag:
                            tag_symbols, _ = get_table_symbols(mib, metric_tag['table'])
                            tag_symbols.append(oid)
                        elif mib != metric['MIB']:
                            raise ConfigurationError('When tagging from a different MIB, the table must be specified')
                        else:
                            symbols.append(oid)

                    elif 'index' in metric_tag:
                        index_tags.append((tag_key, metric_tag['index']))

                        if 'mapping' in metric_tag:
                            # Need to do manual resolution

                            for symbol in metric['symbols']:
                                self._resolver.register_index(
                                    symbol['name'], metric_tag['index'], metric_tag['mapping']
                                )

                            for tag in metric['metric_tags']:
                                if 'column' in tag:
                                    self._resolver.register_index(
                                        tag['column']['name'], metric_tag['index'], metric_tag['mapping']
                                    )

                for symbol in metric['symbols']:
                    try:
                        oid, parsed_metric_name = extract_symbol(metric['MIB'], symbol)
                    except Exception as e:
                        warning("(3) Can't generate MIB object for variable : %s\nException: %s", metric, e)
                    else:
                        symbols.append(oid)
                        parsed_table_metric = ParsedTableMetric(
                            parsed_metric_name, index_tags, column_tags, forced_type
                        )
                        parsed_metrics.append(parsed_table_metric)

            elif 'OID' in metric:
                oid = OID(metric['OID'])

                table_oids[metric['OID']] = (oid, [])
                self._resolver.register(oid, metric['name'])

                parsed_metric = ParsedMetric(metric['name'], metric_tags, forced_type, enforce_scalar=False)
                parsed_metrics.append(parsed_metric)

            else:
                raise ConfigurationError('Unsupported metric in config file: {}'.format(metric))

        all_oids = []  # type: List[OID]
        bulk_oids = []  # type: List[OID]

        # Use bulk for SNMP version > 1 and there are enough symbols
        bulk_limit = self.bulk_threshold if self._auth_data.mpModel else 0

        for table_oid, symbols in table_oids.values():
            if not symbols:
                # No table to browse, just one symbol
                all_oids.append(table_oid)
            elif bulk_limit and len(symbols) > bulk_limit:
                bulk_oids.append(table_oid)
            else:
                all_oids.extend(symbols)

        return all_oids, bulk_oids, parsed_metrics

    def parse_metric_tags(self, metric_tags):
        # type: (List[Dict[str, Any]]) -> Tuple[List[OID], List[ParsedMetricTag]]
        """Parse configuration for global metric_tags."""
        oids = []  # type: List[OID]

        parsed_metric_tags = []  # type: List[ParsedMetricTag]

        for tag in metric_tags:
            if not ('symbol' in tag and 'tag' in tag):
                raise ConfigurationError("A metric tag needs to specify a symbol and a tag: {}".format(tag))
            if not ('OID' in tag or 'MIB' in tag):
                raise ConfigurationError("A metric tag needs to specify an OID or a MIB: {}".format(tag))

            symbol = tag['symbol']  # type: str
            tag_name = tag['tag']  # type: str

            if 'MIB' in tag:
                mib = tag['MIB']  # type: str
                oid = OID(ObjectIdentity(mib, symbol))
            else:
                oid = OID(tag['OID'])
                self._resolver.register(oid, symbol)

            oids.append(oid)
            parsed_metric_tags.append(ParsedMetricTag(tag_name, symbol))

        return oids, parsed_metric_tags

    def add_uptime_metric(self):
        # type: () -> None
        if self._uptime_metric_added:
            return
        # Reference sysUpTimeInstance directly, see http://oidref.com/1.3.6.1.2.1.1.3.0
        uptime_oid = OID('1.3.6.1.2.1.1.3.0')
        self.all_oids.append(uptime_oid)
        self._resolver.register(uptime_oid, 'sysUpTimeInstance')

        parsed_metric = ParsedMetric('sysUpTimeInstance', [], 'gauge')
        self.parsed_metrics.append(parsed_metric)
        self._uptime_metric_added = True
