# (C) Datadog, Inc. 2010-2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from pyasn1.type.univ import OctetString
from pysnmp import hlapi
from pysnmp.smi import builder, view

from datadog_checks.base import ConfigurationError, is_affirmative


class InstanceConfig:
    """Parse and hold configuration about a single instance."""

    DEFAULT_RETRIES = 5
    DEFAULT_TIMEOUT = 1

    def __init__(self, instance, warning, global_metrics, mibs_path, profiles):
        self.tags = instance.get('tags', [])
        self.metrics = instance.get('metrics', [])
        self.profile = instance.get('profile')
        if is_affirmative(instance.get('use_global_metrics', True)):
            self.metrics.extend(global_metrics)
        if self.profile:
            if self.profile not in profiles:
                raise ConfigurationError("Unknown profile '{}'".format(self.profile))
            self.metrics.extend(profiles[self.profile]['definition'])
        self.enforce_constraints = is_affirmative(instance.get('enforce_mib_constraints', True))
        self.snmp_engine, self.mib_view_controller = self.create_snmp_engine(mibs_path)

        timeout = int(instance.get('timeout', self.DEFAULT_TIMEOUT))
        retries = int(instance.get('retries', self.DEFAULT_RETRIES))
        self.transport = self.get_transport_target(instance, timeout, retries)

        self.ip_address = instance['ip_address']
        self.table_oids, self.raw_oids, self.mibs_to_load = self.parse_metrics(
            self.metrics, self.enforce_constraints, warning
        )
        self.tags.append('snmp_device:{}'.format(self.ip_address))
        self.auth_data = self.get_auth_data(instance)
        self.context_data = hlapi.ContextData(*self.get_context_data(instance))

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
        if 'ip_address' not in instance:
            raise ConfigurationError('An IP address needs to be specified')
        ip_address = instance['ip_address']
        port = int(instance.get('port', 161))  # Default SNMP port
        return hlapi.UdpTransportTarget((ip_address, port), timeout=timeout, retries=retries)

    @staticmethod
    def get_auth_data(instance):
        """
        Generate a Security Parameters object based on the instance's
        configuration.
        See http://pysnmp.sourceforge.net/docs/current/security-configuration.html
        """
        if 'community_string' in instance:
            # SNMP v1 - SNMP v2

            # See http://pysnmp.sourceforge.net/docs/current/security-configuration.html
            if int(instance.get('snmp_version', 2)) == 1:
                return hlapi.CommunityData(instance['community_string'], mpModel=0)
            return hlapi.CommunityData(instance['community_string'], mpModel=1)

        elif 'user' in instance:
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
        else:
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

    @staticmethod
    def parse_metrics(metrics, enforce_constraints, warning):
        if not metrics:
            raise ConfigurationError('Metrics list must contain at least one metric')
        raw_oids = []
        table_oids = []
        mibs_to_load = set()
        # Check the metrics completely defined
        for metric in metrics:
            if 'MIB' in metric:
                if not ('table' in metric or 'symbol' in metric):
                    raise ConfigurationError('When specifying a MIB, you must specify either table or symbol')
                if not enforce_constraints:
                    # We need this only if we don't enforce constraints to be able to lookup MIBs manually
                    mibs_to_load.add(metric['MIB'])
                if 'symbol' in metric:
                    to_query = metric['symbol']
                    try:
                        table_oids.append(hlapi.ObjectType(hlapi.ObjectIdentity(metric['MIB'], to_query)))
                    except Exception as e:
                        warning("Can't generate MIB object for variable : %s\nException: %s", metric, e)
                elif 'symbols' not in metric:
                    raise ConfigurationError('When specifying a table, you must specify a list of symbols')
                else:
                    for symbol in metric['symbols']:
                        try:
                            table_oids.append(hlapi.ObjectType(hlapi.ObjectIdentity(metric['MIB'], symbol)))
                        except Exception as e:
                            warning("Can't generate MIB object for variable : %s\nException: %s", metric, e)
                    if 'metric_tags' in metric:
                        for metric_tag in metric['metric_tags']:
                            if not ('tag' in metric_tag and ('index' in metric_tag or 'column' in metric_tag)):
                                raise ConfigurationError(
                                    'When specifying metric tags, you must specify a tag, and an index or column'
                                )
                            if 'column' in metric_tag:
                                # In case it's a column, we need to query it as well
                                try:
                                    table_oids.append(
                                        hlapi.ObjectType(hlapi.ObjectIdentity(metric['MIB'], metric_tag.get('column')))
                                    )
                                except Exception as e:
                                    warning("Can't generate MIB object for variable : %s\nException: %s", metric, e)

            elif 'OID' in metric:
                raw_oids.append(hlapi.ObjectType(hlapi.ObjectIdentity(metric['OID'])))
            else:
                raise ConfigurationError('Unsupported metric in config file: {}'.format(metric))

        return table_oids, raw_oids, mibs_to_load
