# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from collections import defaultdict

import pysnmp.proto.rfc1902 as snmp_type
from pyasn1.codec.ber import decoder
from pyasn1.type.univ import OctetString
from pysnmp import hlapi
from pysnmp.error import PySnmpError
from pysnmp.smi import builder, view
from pysnmp.smi.exval import noSuchInstance, noSuchObject
from six import iteritems

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.errors import CheckException

# Additional types that are not part of the SNMP protocol. cf RFC 2856
CounterBasedGauge64, ZeroBasedCounter64 = builder.MibBuilder().importSymbols(
    'HCNUM-TC', 'CounterBasedGauge64', 'ZeroBasedCounter64'
)

# Metric type that we support
SNMP_COUNTERS = frozenset([snmp_type.Counter32.__name__, snmp_type.Counter64.__name__, ZeroBasedCounter64.__name__])

SNMP_GAUGES = frozenset(
    [
        snmp_type.Gauge32.__name__,
        snmp_type.Unsigned32.__name__,
        CounterBasedGauge64.__name__,
        snmp_type.Integer.__name__,
        snmp_type.Integer32.__name__,
    ]
)

DEFAULT_OID_BATCH_SIZE = 10


def reply_invalid(oid):
    return noSuchInstance.isSameTypeWith(oid) or noSuchObject.isSameTypeWith(oid)


class InstanceConfig:
    """Parse and hold configuration about a single instance."""

    DEFAULT_RETRIES = 5
    DEFAULT_TIMEOUT = 1

    def __init__(self, instance, warning, global_metrics, mibs_path):
        self.instance = instance

        self.tags = instance.get('tags', [])
        self.metrics = instance.get('metrics', [])
        if is_affirmative(instance.get('use_global_metrics', True)):
            self.metrics.extend(global_metrics)
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


class SnmpCheck(AgentCheck):

    SOURCE_TYPE_NAME = 'system'
    # pysnmp default values
    SC_STATUS = 'snmp.can_check'

    def __init__(self, name, init_config, instances):
        # Set OID batch size
        self.oid_batch_size = int(init_config.get('oid_batch_size', DEFAULT_OID_BATCH_SIZE))

        # Load Custom MIB directory
        self.mibs_path = None
        self.ignore_nonincreasing_oid = False
        if init_config is not None:
            self.mibs_path = init_config.get('mibs_folder')
            self.ignore_nonincreasing_oid = is_affirmative(init_config.get('ignore_nonincreasing_oid', False))

        self._conf = {}

        for instance in instances:
            self._load_conf(instance)

        super(SnmpCheck, self).__init__(name, init_config, instances)

    def _load_conf(self, instance):
        if 'name' not in instance:
            instance['name'] = self._get_instance_key(instance)
        if instance['name'] not in self._conf:
            self._conf[instance['name']] = InstanceConfig(
                instance, self.warning, self.init_config.get('global_metrics', []), self.mibs_path
            )
        return self._conf[instance['name']]

    def _get_instance_key(self, instance):
        key = instance.get('name')
        if key:
            return key

        ip = instance.get('ip_address')
        port = instance.get('port')
        if ip and port:
            key = '{host}:{port}'.format(host=ip, port=port)
        elif ip:
            key = ip

        return key

    def raise_on_error_indication(self, error_indication, instance):
        if error_indication:
            message = '{} for instance {}'.format(error_indication, instance['ip_address'])
            instance['service_check_error'] = message
            raise CheckException(message)

    def check_table(self, oids, config, lookup_names, enforce_constraints):
        """
        Perform a snmpwalk on the domain specified by the oids, on the device
        configured in instance.
        lookup_names is a boolean to specify whether or not to use the mibs to
        resolve the name and values.

        Returns a dictionary:
        dict[oid/metric_name][row index] = value
        In case of scalar objects, the row index is just 0
        """
        # UPDATE: We used to perform only a snmpgetnext command to fetch metric values.
        # It returns the wrong value when the OID passeed is referring to a specific leaf.
        # For example:
        # snmpgetnext -v2c -c public localhost:11111 1.3.6.1.2.1.25.4.2.1.7.222
        # iso.3.6.1.2.1.25.4.2.1.7.224 = INTEGER: 2
        # SOLUTION: perform a snmpget command and fallback with snmpgetnext if not found

        # Set aliases for snmpget and snmpgetnext with logging

        first_oid = 0
        all_binds = []
        results = defaultdict(dict)

        while first_oid < len(oids):
            try:
                oids_batch = oids[first_oid : first_oid + self.oid_batch_size]
                self.log.debug('Running SNMP command get on OIDS %s', oids_batch)
                error_indication, error_status, error_index, var_binds = next(
                    hlapi.getCmd(
                        config.snmp_engine,
                        config.auth_data,
                        config.transport,
                        config.context_data,
                        *oids_batch,
                        lookupMib=enforce_constraints
                    )
                )
                self.log.debug('Returned vars: %s', var_binds)

                # Raise on error_indication
                self.raise_on_error_indication(error_indication, config.instance)

                missing_results = []
                complete_results = []

                for var in var_binds:
                    result_oid, value = var
                    if reply_invalid(value):
                        oid_tuple = result_oid.asTuple()
                        missing_results.append(hlapi.ObjectType(hlapi.ObjectIdentity(oid_tuple)))
                    else:
                        complete_results.append(var)

                if missing_results:
                    # If we didn't catch the metric using snmpget, try snmpnext
                    self.log.debug('Running SNMP command getNext on OIDS %s', missing_results)
                    for error_indication, error_status, _, var_binds_table in hlapi.nextCmd(
                        config.snmp_engine,
                        config.auth_data,
                        config.transport,
                        config.context_data,
                        *missing_results,
                        lookupMib=enforce_constraints,
                        ignoreNonIncreasingOid=self.ignore_nonincreasing_oid,
                        lexicographicMode=False  # Don't walk through the entire MIB, stop at end of table
                    ):

                        self.log.debug('Returned vars: %s', var_binds_table)
                        # Raise on error_indication
                        self.raise_on_error_indication(error_indication, config.instance)

                        if error_status:
                            message = '{} for instance {}'.format(error_status.prettyPrint(), config.ip_address)
                            config.instance['service_check_error'] = message

                            # submit CRITICAL service check if we can't connect to device
                            if 'unknownUserName' in message:
                                self.log.error(message)
                            else:
                                self.warning(message)

                        for table_row in var_binds_table:
                            complete_results.append(table_row)

                all_binds.extend(complete_results)

            except PySnmpError as e:
                if 'service_check_error' not in config.instance:
                    config.instance['service_check_error'] = 'Fail to collect some metrics: {}'.format(e)
                self.warning('Fail to collect some metrics: {}'.format(e))

            # if we fail move onto next batch
            first_oid = first_oid + self.oid_batch_size

        # if we've collected some variables, it's not that bad.
        if 'service_check_error' in config.instance and len(all_binds):
            config.instance['service_check_severity'] = self.WARNING

        for result_oid, value in all_binds:
            if lookup_names:
                if not enforce_constraints:
                    # if enforce_constraints is false, then MIB resolution has not been done yet
                    # so we need to do it manually. We have to specify the mibs that we will need
                    # to resolve the name.
                    oid_to_resolve = hlapi.ObjectIdentity(result_oid.asTuple()).loadMibs(*config.mibs_to_load)
                    result_oid = oid_to_resolve.resolveWithMib(config.mib_view_controller)
                _, metric, indexes = result_oid.getMibSymbol()
                results[metric][indexes] = value
            else:
                oid = result_oid.asTuple()
                matching = '.'.join([str(i) for i in oid])
                results[matching] = value
        self.log.debug('Raw results: %s', results)
        return results

    def check(self, instance):
        """
        Perform two series of SNMP requests, one for all that have MIB associated
        and should be looked up and one for those specified by oids.
        """
        config = self._load_conf(instance)

        try:
            if config.table_oids:
                self.log.debug('Querying device %s for %s oids', config.ip_address, len(config.table_oids))
                table_results = self.check_table(
                    config.table_oids, config, lookup_names=True, enforce_constraints=config.enforce_constraints
                )
                self.report_table_metrics(config.metrics, table_results, config.tags)

            if config.raw_oids:
                self.log.debug('Querying device %s for %s oids', config.ip_address, len(config.raw_oids))
                raw_results = self.check_table(config.raw_oids, config, lookup_names=False, enforce_constraints=False)
                self.report_raw_metrics(config.metrics, raw_results, config.tags)
        except Exception as e:
            if 'service_check_error' not in instance:
                instance['service_check_error'] = 'Fail to collect metrics for {} - {}'.format(instance['name'], e)
            self.warning(instance['service_check_error'])
        finally:
            # Report service checks
            sc_tags = ['snmp_device:{}'.format(instance['ip_address'])]
            sc_tags.extend(instance.get('tags', []))
            status = self.OK
            msg = instance.get('service_check_error')
            if msg:
                status = self.CRITICAL
                if 'service_check_severity' in instance:
                    status = instance['service_check_severity']
            self.service_check(self.SC_STATUS, status, tags=sc_tags, message=msg)

    def report_raw_metrics(self, metrics, results, tags):
        """
        For all the metrics that are specified as oid,
        the conf oid is going to exactly match or be a prefix of the oid sent back by the device
        Use the instance configuration to find the name to give to the metric

        Submit the results to the aggregator.
        """
        for metric in metrics:
            forced_type = metric.get('forced_type')
            if 'OID' in metric:
                queried_oid = metric['OID'].lstrip('.')
                if queried_oid in results:
                    value = results[queried_oid]
                else:
                    for oid in results:
                        if oid.startswith(queried_oid):
                            value = results[oid]
                            break
                    else:
                        self.log.warning('No matching results found for oid %s', queried_oid)
                        continue
                name = metric.get('name', 'unnamed_metric')
                metric_tags = tags
                if metric.get('metric_tags'):
                    metric_tags = metric_tags + metric.get('metric_tags')
                self.submit_metric(name, value, forced_type, metric_tags)

    def report_table_metrics(self, metrics, results, tags):
        """
        For each of the metrics specified as needing to be resolved with mib,
        gather the tags requested in the instance conf for each row.

        Submit the results to the aggregator.
        """
        for metric in metrics:
            forced_type = metric.get('forced_type')
            if 'table' in metric:
                index_based_tags = []
                column_based_tags = []
                for metric_tag in metric.get('metric_tags', []):
                    tag_key = metric_tag['tag']
                    if 'index' in metric_tag:
                        index_based_tags.append((tag_key, metric_tag.get('index')))
                    elif 'column' in metric_tag:
                        column_based_tags.append((tag_key, metric_tag.get('column')))
                    else:
                        self.log.warning('No indication on what value to use for this tag')

                for value_to_collect in metric.get('symbols', []):
                    for index, val in iteritems(results[value_to_collect]):
                        metric_tags = tags + self.get_index_tags(index, results, index_based_tags, column_based_tags)
                        self.submit_metric(value_to_collect, val, forced_type, metric_tags)

            elif 'symbol' in metric:
                name = metric['symbol']
                result = list(results[name].items())
                if len(result) > 1:
                    self.log.warning('Several rows corresponding while the metric is supposed to be a scalar')
                    continue
                val = result[0][1]
                metric_tags = tags
                if metric.get('metric_tags'):
                    metric_tags = metric_tags + metric.get('metric_tags')
                self.submit_metric(name, val, forced_type, metric_tags)
            elif 'OID' in metric:
                pass  # This one is already handled by the other batch of requests
            else:
                raise ConfigurationError('Unsupported metric in config file: {}'.format(metric))

    def get_index_tags(self, index, results, index_tags, column_tags):
        """
        Gather the tags for this row of the table (index) based on the
        results (all the results from the query).
        index_tags and column_tags are the tags to gather.
         - Those specified in index_tags contain the tag_group name and the
           index of the value we want to extract from the index tuple.
           cf. 1 for ipVersion in the IP-MIB::ipSystemStatsTable for example
         - Those specified in column_tags contain the name of a column, which
           could be a potential result, to use as a tage
           cf. ifDescr in the IF-MIB::ifTable for example
        """
        tags = []
        for idx_tag in index_tags:
            tag_group = idx_tag[0]
            try:
                tag_value = index[idx_tag[1] - 1].prettyPrint()
            except IndexError:
                self.log.warning('Not enough indexes, skipping this tag')
                continue
            tags.append('{}:{}'.format(tag_group, tag_value))
        for col_tag in column_tags:
            tag_group = col_tag[0]
            try:
                tag_value = results[col_tag[1]][index]
            except KeyError:
                self.log.warning('Column %s not present in the table, skipping this tag', col_tag[1])
                continue
            if reply_invalid(tag_value):
                self.log.warning("Can't deduct tag from column for tag %s", tag_group)
                continue
            tag_value = tag_value.prettyPrint()
            tags.append('{}:{}'.format(tag_group, tag_value))
        return tags

    def submit_metric(self, name, snmp_value, forced_type, tags=None):
        """
        Convert the values reported as pysnmp-Managed Objects to values and
        report them to the aggregator.
        """
        tags = [] if tags is None else tags
        if reply_invalid(snmp_value):
            # Metrics not present in the queried object
            self.log.warning('No such Mib available: %s', name)
            return

        metric_name = self.normalize(name, prefix='snmp')

        if forced_type:
            if forced_type.lower() == 'gauge':
                value = int(snmp_value)
                self.gauge(metric_name, value, tags)
            elif forced_type.lower() == 'counter':
                value = int(snmp_value)
                self.rate(metric_name, value, tags)
            else:
                self.warning('Invalid forced-type specified: {} in {}'.format(forced_type, name))
                raise ConfigurationError('Invalid forced-type in config file: {}'.format(name))
            return

        # Ugly hack but couldn't find a cleaner way
        # Proper way would be to use the ASN1 method isSameTypeWith but it
        # wrongfully returns True in the case of CounterBasedGauge64
        # and Counter64 for example
        snmp_class = snmp_value.__class__.__name__
        if snmp_class in SNMP_COUNTERS:
            value = int(snmp_value)
            self.rate(metric_name, value, tags)
            return
        if snmp_class in SNMP_GAUGES:
            value = int(snmp_value)
            self.gauge(metric_name, value, tags)
            return

        if snmp_class == 'Opaque':
            # Try support for floats
            try:
                value = float(decoder.decode(bytes(snmp_value))[0])
            except Exception:
                pass
            else:
                self.gauge(metric_name, value, tags)
                return

        # Falls back to try to cast the value.
        try:
            value = float(snmp_value)
        except ValueError:
            pass
        else:
            self.gauge(metric_name, value, tags)
            return

        self.log.warning('Unsupported metric type %s for %s', snmp_class, metric_name)
