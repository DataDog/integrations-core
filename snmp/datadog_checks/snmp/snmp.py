# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import fnmatch
import ipaddress
import json
import threading
import time
from collections import defaultdict

import pysnmp.proto.rfc1902 as snmp_type
from pyasn1.codec.ber import decoder
from pysnmp import hlapi
from pysnmp.error import PySnmpError
from pysnmp.smi import builder
from pysnmp.smi.exval import endOfMibView, noSuchInstance, noSuchObject
from six import iteritems

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.errors import CheckException

from .compat import read_persistent_cache, total_time_to_temporal_percent, write_persistent_cache
from .config import InstanceConfig, ParsedTableMetric
from .utils import get_profile_definition

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
    _running = True
    _thread = None
    _NON_REPEATERS = 0
    _MAX_REPETITIONS = 25

    def __init__(self, name, init_config, instances):
        super(SnmpCheck, self).__init__(name, init_config, instances)

        # Set OID batch size
        self.oid_batch_size = int(init_config.get('oid_batch_size', DEFAULT_OID_BATCH_SIZE))

        # Load Custom MIB directory
        self.mibs_path = init_config.get('mibs_folder')

        self.ignore_nonincreasing_oid = is_affirmative(init_config.get('ignore_nonincreasing_oid', False))

        self.profiles = init_config.get('profiles', {})
        self.profiles_by_oid = {}
        self._load_profiles()

        self.instance['name'] = self._get_instance_key(self.instance)
        self._config = self._build_config(self.instance)

    def _load_profiles(self):
        """
        Load the configured SNMP profiles and index them by sysObjectID, if possible.
        """
        for name, profile in self.profiles.items():
            try:
                definition = get_profile_definition(profile)
            except Exception as exc:
                raise ConfigurationError("Couldn't read profile '{}': {}".format(name, exc))

            self.profiles[name] = {'definition': definition}

            sys_object_oid = definition.get('sysobjectid')
            if sys_object_oid is not None:
                self.profiles_by_oid[sys_object_oid] = name

    def _build_config(self, instance):
        return InstanceConfig(
            instance,
            self.warning,
            self.log,
            self.init_config.get('global_metrics', []),
            self.mibs_path,
            self.profiles,
            self.profiles_by_oid,
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

    def discover_instances(self):
        config = self._config
        discovery_interval = config.instance.get('discovery_interval', 3600)
        while self._running:
            start_time = time.time()
            for host in config.ip_network.hosts():
                host = str(host)
                if host in config.discovered_instances:
                    continue
                instance = config.instance.copy()
                instance.pop('network_address')
                instance['ip_address'] = host

                host_config = self._build_config(instance)
                try:
                    sys_object_oid = self.fetch_sysobject_oid(host_config)
                except Exception as e:
                    self.log.debug("Error scanning host %s: %s", host, e)
                    continue
                try:
                    profile = self._profile_for_sysobject_oid(sys_object_oid)
                except ConfigurationError:
                    if not (host_config.all_oids or host_config.bulk_oids):
                        self.log.warning("Host %s didn't match a profile for sysObjectID %s", host, sys_object_oid)
                        continue
                else:
                    host_config.refresh_with_profile(self.profiles[profile], self.warning, self.log)
                config.discovered_instances[host] = host_config

                write_persistent_cache(self.check_id, json.dumps(list(config.discovered_instances)))

            # Write again at the end of the loop, in case some host have been removed since last
            write_persistent_cache(self.check_id, json.dumps(list(config.discovered_instances)))

            time_elapsed = time.time() - start_time
            if discovery_interval - time_elapsed > 0:
                time.sleep(discovery_interval - time_elapsed)

    def raise_on_error_indication(self, error_indication, ip_address):
        if error_indication:
            message = '{} for instance {}'.format(error_indication, ip_address)
            raise CheckException(message)

    def fetch_results(self, config, all_oids, bulk_oids):
        """
        Perform a snmpwalk on the domain specified by the oids, on the device
        configured in instance.

        Returns a dictionary:
        dict[oid/metric_name][row index] = value
        In case of scalar objects, the row index is just 0
        """
        results = defaultdict(dict)
        enforce_constraints = config.enforce_constraints

        all_binds = []
        error = None
        for to_fetch in all_oids:
            binds, current_error = self.fetch_oids(config, to_fetch, enforce_constraints=enforce_constraints)
            all_binds.extend(binds)
            error = current_error if not error else error

        for oid in bulk_oids:
            try:
                self.log.debug('Running SNMP command getBulk on OID %r', oid)
                binds_iterator = config.call_cmd(
                    hlapi.bulkCmd,
                    self._NON_REPEATERS,
                    self._MAX_REPETITIONS,
                    oid,
                    lookupMib=enforce_constraints,
                    ignoreNonIncreasingOid=self.ignore_nonincreasing_oid,
                    lexicographicMode=False,
                )
                binds, current_error = self._consume_binds_iterator(binds_iterator, config)
                all_binds.extend(binds)
                error = current_error if not error else error

            except PySnmpError as e:
                message = 'Failed to collect some metrics: {}'.format(e)
                if not error:
                    error = message
                self.warning(message)

        for result_oid, value in all_binds:
            metric, indexes = config.resolve_oid(result_oid)
            results[metric][indexes] = value
        self.log.debug('Raw results: %s', results)
        # Freeze the result
        results.default_factory = None
        return results, error

    def fetch_oids(self, config, oids, enforce_constraints):
        # UPDATE: We used to perform only a snmpgetnext command to fetch metric values.
        # It returns the wrong value when the OID passeed is referring to a specific leaf.
        # For example:
        # snmpgetnext -v2c -c public localhost:11111 1.3.6.1.2.1.25.4.2.1.7.222
        # iso.3.6.1.2.1.25.4.2.1.7.224 = INTEGER: 2
        # SOLUTION: perform a snmpget command and fallback with snmpgetnext if not found
        error = None
        first_oid = 0
        all_binds = []
        while first_oid < len(oids):
            try:
                oids_batch = oids[first_oid : first_oid + self.oid_batch_size]
                self.log.debug('Running SNMP command get on OIDS %s', oids_batch)
                error_indication, error_status, _, var_binds = next(
                    config.call_cmd(hlapi.getCmd, *oids_batch, lookupMib=enforce_constraints)
                )
                self.log.debug('Returned vars: %s', var_binds)

                self.raise_on_error_indication(error_indication, config.ip_address)

                missing_results = []

                for var in var_binds:
                    result_oid, value = var
                    if reply_invalid(value):
                        oid_tuple = result_oid.asTuple()
                        missing_results.append(hlapi.ObjectType(hlapi.ObjectIdentity(oid_tuple)))
                    else:
                        all_binds.append(var)

                if missing_results:
                    # If we didn't catch the metric using snmpget, try snmpnext
                    # Don't walk through the entire MIB, stop at end of table
                    self.log.debug('Running SNMP command getNext on OIDS %s', missing_results)
                    binds_iterator = config.call_cmd(
                        hlapi.nextCmd,
                        *missing_results,
                        lookupMib=enforce_constraints,
                        ignoreNonIncreasingOid=self.ignore_nonincreasing_oid,
                        lexicographicMode=False
                    )
                    binds, error = self._consume_binds_iterator(binds_iterator, config)
                    all_binds.extend(binds)

            except PySnmpError as e:
                message = 'Failed to collect some metrics: {}'.format(e)
                if not error:
                    error = message
                self.warning(message)

            # if we fail move onto next batch
            first_oid += self.oid_batch_size

        return all_binds, error

    def fetch_sysobject_oid(self, config):
        """Return the sysObjectID of the instance."""
        # Reference sysObjectID directly, see http://oidref.com/1.3.6.1.2.1.1.2
        oid = hlapi.ObjectType(hlapi.ObjectIdentity((1, 3, 6, 1, 2, 1, 1, 2)))
        self.log.debug('Running SNMP command on OID %r', oid)
        error_indication, _, _, var_binds = next(config.call_cmd(hlapi.nextCmd, oid, lookupMib=False))
        self.raise_on_error_indication(error_indication, config.ip_address)
        self.log.debug('Returned vars: %s', var_binds)
        return var_binds[0][1].prettyPrint()

    def _profile_for_sysobject_oid(self, sys_object_oid):
        """Return, if any, a matching profile for sys_object_oid.

        If several profiles match, it will return the longer match, ie the
        closest one to the sys_object_oid.
        """
        oids = [oid for oid in self.profiles_by_oid if fnmatch.fnmatch(sys_object_oid, oid)]
        oids.sort()
        if not oids:
            raise ConfigurationError('No profile matching sysObjectID {}'.format(sys_object_oid))
        return self.profiles_by_oid[oids[-1]]

    def _consume_binds_iterator(self, binds_iterator, config):
        all_binds = []
        error = None
        for error_indication, error_status, _, var_binds_table in binds_iterator:
            self.log.debug('Returned vars: %s', var_binds_table)

            self.raise_on_error_indication(error_indication, config.ip_address)

            if error_status:
                message = '{} for instance {}'.format(error_status.prettyPrint(), config.ip_address)
                error = message

                # submit CRITICAL service check if we can't connect to device
                if 'unknownUserName' in message:
                    self.log.error(message)
                else:
                    self.warning(message)

            all_binds.extend(var_bind for var_bind in var_binds_table if var_bind[1] is not endOfMibView)
        return all_binds, error

    def _start_discovery(self):
        cache = read_persistent_cache(self.check_id)
        if cache:
            hosts = json.loads(cache)
            for host in hosts:
                try:
                    ipaddress.ip_address(host)
                except ValueError:
                    write_persistent_cache(self.check_id, json.dumps([]))
                    break
                instance = self.instance.copy()
                instance.pop('network_address')
                instance['ip_address'] = host

                host_config = self._build_config(instance)
                self._config.discovered_instances[host] = host_config

        self._thread = threading.Thread(target=self.discover_instances, name=self.name)
        self._thread.daemon = True
        self._thread.start()

    def check(self, instance):
        config = self._config
        if config.ip_network:
            if self._thread is None:
                self._start_discovery()
            for host, discovered in list(config.discovered_instances.items()):
                if self._check_with_config(discovered):
                    config.failing_instances[host] += 1
                    if config.failing_instances[host] >= config.allowed_failures:
                        # Remove it from discovered instances, we'll re-discover it later if it reappears
                        config.discovered_instances.pop(host)
                        # Reset the failure counter as well
                        config.failing_instances.pop(host)
                else:
                    # Reset the counter if not's failing
                    config.failing_instances.pop(host, None)
            tags = ['network:{}'.format(config.ip_network)]
            tags.extend(config.tags)
            self.gauge('snmp.discovered_devices_count', len(config.discovered_instances), tags=tags)
        else:
            self._check_with_config(config)

    def _check_with_config(self, config):
        # Reset errors
        instance = config.instance
        error = results = None
        try:
            if not (config.all_oids or config.bulk_oids):
                sys_object_oid = self.fetch_sysobject_oid(config)
                profile = self._profile_for_sysobject_oid(sys_object_oid)
                config.refresh_with_profile(self.profiles[profile], self.warning, self.log)

            if config.all_oids or config.bulk_oids:
                self.log.debug('Querying device %s', config.ip_address)
                results, error = self.fetch_results(config, config.all_oids, config.bulk_oids)
                self.report_metrics(config.parsed_metrics, results, config.tags)
        except CheckException as e:
            error = str(e)
            self.warning(error)
        except Exception as e:
            if not error:
                error = 'Failed to collect metrics for {} - {}'.format(instance['name'], e)
            self.warning(error)
        finally:
            # Report service checks
            sc_tags = ['snmp_device:{}'.format(instance['ip_address'])]
            sc_tags.extend(instance.get('tags', []))
            status = self.OK
            if error:
                status = self.CRITICAL
                if results:
                    status = self.WARNING
            self.service_check(self.SC_STATUS, status, tags=sc_tags, message=error)
        return error

    def report_metrics(self, metrics, results, tags):
        """
        For each of the metrics specified gather the tags requested in the
        instance conf for each row.

        Submit the results to the aggregator.
        """
        for metric in metrics:
            name = metric.name
            if name not in results:
                self.log.debug('Ignoring metric %s', name)
                continue
            if isinstance(metric, ParsedTableMetric):
                for index, val in iteritems(results[name]):
                    metric_tags = tags + self.get_index_tags(index, results, metric.index_tags, metric.column_tags)
                    self.submit_metric(name, val, metric.forced_type, metric_tags)
            else:
                result = list(results[name].items())
                if len(result) > 1:
                    self.log.warning('Several rows corresponding while the metric is supposed to be a scalar')
                    if metric.enforce_scalar:
                        # For backward compatibility reason, we publish the first value for OID.
                        continue
                val = result[0][1]
                metric_tags = tags + metric.metric_tags
                self.submit_metric(name, val, metric.forced_type, metric_tags)

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
                tag_value = index[idx_tag[1] - 1]
            except IndexError:
                self.log.warning('Not enough indexes, skipping tag %s', tag_group)
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

    def submit_metric(self, name, snmp_value, forced_type, tags):
        """
        Convert the values reported as pysnmp-Managed Objects to values and
        report them to the aggregator.
        """
        if reply_invalid(snmp_value):
            # Metrics not present in the queried object
            self.log.warning('No such Mib available: %s', name)
            return

        metric_name = self.normalize(name, prefix='snmp')

        if forced_type:
            forced_type = forced_type.lower()
            if forced_type == 'gauge':
                value = int(snmp_value)
                self.gauge(metric_name, value, tags)
            elif forced_type == 'percent':
                value = total_time_to_temporal_percent(int(snmp_value), scale=1)
                self.rate(metric_name, value, tags)
            elif forced_type == 'counter':
                value = int(snmp_value)
                self.rate(metric_name, value, tags)
            elif forced_type == 'monotonic_count':
                value = int(snmp_value)
                self.monotonic_count(metric_name, value, tags)
            else:
                self.warning('Invalid forced-type specified: %s in %s', forced_type, name)
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
