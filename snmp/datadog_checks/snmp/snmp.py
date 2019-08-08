# (C) Datadog, Inc. 2010-2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from collections import defaultdict

import pysnmp.proto.rfc1902 as snmp_type
import yaml
from pyasn1.codec.ber import decoder
from pysnmp import hlapi
from pysnmp.error import PySnmpError
from pysnmp.smi import builder
from pysnmp.smi.exval import noSuchInstance, noSuchObject
from six import iteritems

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.errors import CheckException

from .config import InstanceConfig

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


class SnmpCheck(AgentCheck):

    SC_STATUS = 'snmp.can_check'
    _error = None
    _severity = None

    def __init__(self, name, init_config, instances):
        super(SnmpCheck, self).__init__(name, init_config, instances)

        # Set OID batch size
        self.oid_batch_size = int(init_config.get('oid_batch_size', DEFAULT_OID_BATCH_SIZE))

        # Load Custom MIB directory
        self.mibs_path = init_config.get('mibs_folder')
        self.ignore_nonincreasing_oid = is_affirmative(init_config.get('ignore_nonincreasing_oid', False))
        self.profiles = init_config.get('profiles', {})
        for profile, profile_data in list(self.profiles.items()):
            filename = profile_data['definition']
            try:
                with open(filename) as f:
                    data = yaml.safe_load(f)
            except Exception:
                raise ConfigurationError("Couldn't read profile '{}' in '{}'".format(profile, filename))
            self.profiles[profile] = {'definition': data}

        self.instance['name'] = self._get_instance_key(self.instance)
        self._config = InstanceConfig(
            self.instance, self.warning, self.init_config.get('global_metrics', []), self.mibs_path, self.profiles
        )

    def _get_instance_key(self, instance):
        key = instance.get('name')
        if key:
            return key

        ip = instance.get('ip_address')
        port = instance.get('port')
        if ip and port:
            key = '{host}:{port}'.format(host=ip, port=port)
        else:
            key = ip

        return key

    def raise_on_error_indication(self, error_indication, ip_address):
        if error_indication:
            message = '{} for instance {}'.format(error_indication, ip_address)
            self._error = message
            raise CheckException(message)

    def check_table(self, oids, lookup_names, enforce_constraints):
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
        config = self._config

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
                self.raise_on_error_indication(error_indication, config.ip_address)

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
                        self.raise_on_error_indication(error_indication, config.ip_address)

                        if error_status:
                            message = '{} for instance {}'.format(error_status.prettyPrint(), config.ip_address)
                            self._error = message

                            # submit CRITICAL service check if we can't connect to device
                            if 'unknownUserName' in message:
                                self.log.error(message)
                            else:
                                self.warning(message)

                        for table_row in var_binds_table:
                            complete_results.append(table_row)

                all_binds.extend(complete_results)

            except PySnmpError as e:
                if not self._error:
                    self._error = 'Fail to collect some metrics: {}'.format(e)
                self.warning('Fail to collect some metrics: {}'.format(e))

            # if we fail move onto next batch
            first_oid = first_oid + self.oid_batch_size

        # if we've collected some variables, it's not that bad.
        if self._error and all_binds:
            self._severity = self.WARNING

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
        # Reset errors
        self._error = self._severity = None
        config = self._config
        try:
            if config.table_oids:
                self.log.debug('Querying device %s for %s oids', config.ip_address, len(config.table_oids))
                table_results = self.check_table(
                    config.table_oids, lookup_names=True, enforce_constraints=config.enforce_constraints
                )
                self.report_table_metrics(config.metrics, table_results, config.tags)

            if config.raw_oids:
                self.log.debug('Querying device %s for %s oids', config.ip_address, len(config.raw_oids))
                raw_results = self.check_table(config.raw_oids, lookup_names=False, enforce_constraints=False)
                self.report_raw_metrics(config.metrics, raw_results, config.tags)
        except Exception as e:
            if not self._error:
                self._error = 'Fail to collect metrics for {} - {}'.format(instance['name'], e)
            self.warning(self._error)
        finally:
            # Report service checks
            sc_tags = ['snmp_device:{}'.format(instance['ip_address'])]
            sc_tags.extend(instance.get('tags', []))
            status = self.OK
            if self._error:
                status = self.CRITICAL
                if self._severity:
                    status = self._severity
            self.service_check(self.SC_STATUS, status, tags=sc_tags, message=self._error)

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
