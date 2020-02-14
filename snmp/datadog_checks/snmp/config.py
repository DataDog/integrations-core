# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import ipaddress
from collections import defaultdict

from pyasn1.type.univ import OctetString
from pysnmp import hlapi
from pysnmp.smi import builder, view

from datadog_checks.base import ConfigurationError, is_affirmative

from .resolver import OIDResolver


def to_oid_tuple(oid_string):
    """Return a OID tuple from a OID string."""
    return tuple(map(int, oid_string.lstrip('.').split('.')))


class ParsedMetric(object):

    __slots__ = ('name', 'metric_tags', 'forced_type', 'enforce_scalar')

    def __init__(self, name, metric_tags, forced_type, enforce_scalar=True):
        self.name = name
        self.metric_tags = metric_tags
        self.forced_type = forced_type
        self.enforce_scalar = enforce_scalar


class ParsedTableMetric(object):

    __slots__ = ('name', 'index_tags', 'column_tags', 'forced_type')

    def __init__(self, name, index_tags, column_tags, forced_type):
        self.name = name
        self.index_tags = index_tags
        self.column_tags = column_tags
        self.forced_type = forced_type


class InstanceConfig:
    """Parse and hold configuration about a single instance."""

    DEFAULT_RETRIES = 5
    DEFAULT_TIMEOUT = 1
    DEFAULT_ALLOWED_FAILURES = 3
    DEFAULT_BULK_THRESHOLD = 0

    def __init__(self, instance, warning, log, global_metrics, mibs_path, profiles, profiles_by_oid):
        self.instance = instance
        self.tags = instance.get('tags', [])
        self.metrics = instance.get('metrics', [])

        profile = instance.get('profile')

        if is_affirmative(instance.get('use_global_metrics', True)):
            self.metrics.extend(global_metrics)

        if profile:
            if profile not in profiles:
                raise ConfigurationError("Unknown profile '{}'".format(profile))
            self.metrics.extend(profiles[profile]['definition']['metrics'])

        self.enforce_constraints = is_affirmative(instance.get('enforce_mib_constraints', True))
        self._snmp_engine, mib_view_controller = self.create_snmp_engine(mibs_path)
        self._resolver = OIDResolver(mib_view_controller, self.enforce_constraints)

        self.ip_address = None
        self.ip_network = None

        self.discovered_instances = {}
        self.failing_instances = defaultdict(int)
        self.allowed_failures = int(instance.get('discovery_allowed_failures', self.DEFAULT_ALLOWED_FAILURES))

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

        if not self.metrics and not profiles_by_oid:
            raise ConfigurationError('Instance should specify at least one metric or profiles should be defined')

        self._auth_data = self.get_auth_data(instance)

        self.all_oids, self.bulk_oids, self.parsed_metrics = self.parse_metrics(self.metrics, warning, log)

        self._context_data = hlapi.ContextData(*self.get_context_data(instance))

        self._uptime_metric_added = False

    def resolve_oid(self, oid):
        return self._resolver.resolve_oid(oid)

    def refresh_with_profile(self, profile, warning, log):
        self.metrics.extend(profile['definition']['metrics'])
        self.all_oids, self.bulk_oids, self.parsed_metrics = self.parse_metrics(self.metrics, warning, log)

    def call_cmd(self, cmd, *args, **kwargs):
        return cmd(self._snmp_engine, self._auth_data, self._transport, self._context_data, *args, **kwargs)

    @staticmethod
    def create_snmp_engine(mibs_path):
        """
        Create a command generator to perform all the snmp query.
        If mibs_path is not None, load the mibs present in the custom mibs
        folder. (Need to be in pysnmp format)
        """
        snmp_engine = hlapi.SnmpEngine()
        mib_builder = snmp_engine.getMibBuilder()

        if mibs_path is not None:
            mib_builder.addMibSources(builder.DirMibSource(mibs_path))

        mib_view_controller = view.MibViewController(mib_builder)

        return snmp_engine, mib_view_controller

    @staticmethod
    def get_transport_target(instance, timeout, retries):
        """
        Generate a Transport target object based on the instance's configuration
        """
        ip_address = instance['ip_address']
        port = int(instance.get('port', 161))  # Default SNMP port
        return hlapi.UdpTransportTarget((ip_address, port), timeout=timeout, retries=retries)

    @staticmethod
    def get_auth_data(instance):
        """
        Generate a Security Parameters object based on the instance's
        configuration.
        """
        if 'community_string' in instance:
            # SNMP v1 - SNMP v2
            # See http://snmplabs.com/pysnmp/docs/api-reference.html#pysnmp.hlapi.CommunityData
            if int(instance.get('snmp_version', 2)) == 1:
                return hlapi.CommunityData(instance['community_string'], mpModel=0)
            return hlapi.CommunityData(instance['community_string'], mpModel=1)

        if 'user' in instance:
            # SNMP v3
            user = instance['user']
            auth_key = None
            priv_key = None
            auth_protocol = None
            priv_protocol = None

            if 'authKey' in instance:
                auth_key = instance['authKey']
                auth_protocol = hlapi.usmHMACMD5AuthProtocol

            if 'privKey' in instance:
                priv_key = instance['privKey']
                auth_protocol = hlapi.usmHMACMD5AuthProtocol
                priv_protocol = hlapi.usmDESPrivProtocol

            if 'authProtocol' in instance:
                auth_protocol = getattr(hlapi, instance['authProtocol'])

            if 'privProtocol' in instance:
                priv_protocol = getattr(hlapi, instance['privProtocol'])

            return hlapi.UsmUserData(user, auth_key, priv_key, auth_protocol, priv_protocol)

        raise ConfigurationError('An authentication method needs to be provided')

    @staticmethod
    def get_context_data(instance):
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

    def parse_metrics(self, metrics, warning, log):
        """Parse configuration and returns data to be used for SNMP queries.

        `oids` is a dictionnary of SNMP tables to symbols to query.
        """
        table_oids = {}
        parsed_metrics = []

        def extract_symbol(mib, symbol):
            if isinstance(symbol, dict):
                symbol_oid = symbol['OID']
                symbol = symbol['name']
                self._resolver.register(to_oid_tuple(symbol_oid), symbol)
                identity = hlapi.ObjectIdentity(symbol_oid)
            else:
                identity = hlapi.ObjectIdentity(mib, symbol)

            return identity, symbol

        def get_table_symbols(mib, table):
            identity, table = extract_symbol(mib, table)
            key = (mib, table)

            if key in table_oids:
                return table_oids[key][1], table

            table_object = hlapi.ObjectType(identity)
            symbols = []

            table_oids[key] = (table_object, symbols)

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
                        warning("Can't generate MIB object for variable : %s\nException: %s", metric, e)
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
                        identity, column = extract_symbol(mib, metric_tag['column'])
                        column_tags.append((tag_key, column))

                        try:
                            object_type = hlapi.ObjectType(identity)
                        except Exception as e:
                            warning("Can't generate MIB object for variable : %s\nException: %s", metric, e)
                        else:
                            if 'table' in metric_tag:
                                tag_symbols, _ = get_table_symbols(mib, metric_tag['table'])
                                tag_symbols.append(object_type)
                            elif mib != metric['MIB']:
                                raise ConfigurationError(
                                    'When tagging from a different MIB, the table must be specified'
                                )
                            else:
                                symbols.append(object_type)

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
                    identity, parsed_metric_name = extract_symbol(metric['MIB'], symbol)

                    try:
                        symbols.append(hlapi.ObjectType(identity))
                    except Exception as e:
                        warning("Can't generate MIB object for variable : %s\nException: %s", metric, e)

                    parsed_metric = ParsedTableMetric(parsed_metric_name, index_tags, column_tags, forced_type)
                    parsed_metrics.append(parsed_metric)

            elif 'OID' in metric:
                oid_object = hlapi.ObjectType(hlapi.ObjectIdentity(metric['OID']))

                table_oids[metric['OID']] = (oid_object, [])
                self._resolver.register(to_oid_tuple(metric['OID']), metric['name'])

                parsed_metric = ParsedMetric(metric['name'], metric_tags, forced_type, enforce_scalar=False)
                parsed_metrics.append(parsed_metric)

            else:
                raise ConfigurationError('Unsupported metric in config file: {}'.format(metric))

        oids = []
        all_oids = []
        bulk_oids = []

        # Use bulk for SNMP version > 1 and there are enough symbols
        bulk_limit = self.bulk_threshold if self._auth_data.mpModel else 0

        for table, symbols in table_oids.values():
            if not symbols:
                # No table to browse, just one symbol
                oids.append(table)
            elif bulk_limit and len(symbols) > bulk_limit:
                bulk_oids.append(table)
            else:
                all_oids.append(symbols)

        if oids:
            all_oids.insert(0, oids)

        return all_oids, bulk_oids, parsed_metrics

    def add_uptime_metric(self):
        if self._uptime_metric_added:
            return
        uptime_oid = '1.3.6.1.2.1.1.3.0'
        oid_object = hlapi.ObjectType(hlapi.ObjectIdentity(uptime_oid))
        if not self.all_oids:
            self.all_oids.append([oid_object])
        else:
            self.all_oids[0].append(oid_object)
        self._resolver.register(to_oid_tuple(uptime_oid), 'sysUpTimeInstance')

        parsed_metric = ParsedMetric('sysUpTimeInstance', [], 'gauge')
        self.parsed_metrics.append(parsed_metric)
        self._uptime_metric_added = True
