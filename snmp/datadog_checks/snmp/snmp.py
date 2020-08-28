# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import fnmatch
import functools
import ipaddress
import json
import re
import threading
import weakref
from collections import defaultdict
from concurrent import futures
from typing import Any, DefaultDict, Dict, List, Optional, Tuple

from six import iteritems

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.errors import CheckException

from .commands import snmp_bulk, snmp_get, snmp_getnext
from .compat import read_persistent_cache, write_persistent_cache
from .config import InstanceConfig
from .discovery import discover_instances
from .exceptions import PySnmpError
from .metrics import as_metric_with_forced_type, as_metric_with_inferred_type
from .mibs import MIBLoader
from .models import OID
from .parsing import ColumnTag, IndexTag, ParsedMetric, ParsedTableMetric, SymbolTag
from .pysnmp_types import ObjectIdentity, ObjectType, noSuchInstance, noSuchObject
from .utils import (
    OIDPrinter,
    batches,
    get_default_profiles,
    get_profile_definition,
    oid_pattern_specificity,
    recursively_expand_base_profiles,
)

DEFAULT_OID_BATCH_SIZE = 10


def reply_invalid(oid):
    # type: (Any) -> bool
    return noSuchInstance.isSameTypeWith(oid) or noSuchObject.isSameTypeWith(oid)


class SnmpCheck(AgentCheck):

    SC_STATUS = 'snmp.can_check'
    _running = True
    _thread = None
    _executor = None
    _NON_REPEATERS = 0
    _MAX_REPETITIONS = 25
    _thread_factory = threading.Thread  # Store as an attribute for easier mocking.

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(SnmpCheck, self).__init__(*args, **kwargs)

        # Set OID batch size
        self.oid_batch_size = int(self.init_config.get('oid_batch_size', DEFAULT_OID_BATCH_SIZE))

        # Load Custom MIB directory
        self.mibs_path = self.init_config.get('mibs_folder')

        self.optimize_mib_memory_usage = is_affirmative(self.init_config.get('optimize_mib_memory_usage', False))

        self.ignore_nonincreasing_oid = is_affirmative(self.init_config.get('ignore_nonincreasing_oid', False))

        self.profiles = self._load_profiles()
        self.profiles_by_oid = self._get_profiles_mapping()

        self._config = self._build_config(self.instance)

    def _load_profiles(self):
        # type: () -> Dict[str, Dict[str, Any]]
        """
        Load the configured SNMP profiles.
        """
        configured_profiles = self.init_config.get('profiles')

        if configured_profiles is None:
            return get_default_profiles()

        profiles = {}

        for name, profile in configured_profiles.items():
            try:
                definition = get_profile_definition(profile)
            except Exception as exc:
                raise ConfigurationError("Couldn't read profile '{}': {}".format(name, exc))

            try:
                recursively_expand_base_profiles(definition)
            except Exception as exc:
                raise ConfigurationError("Failed to expand base profiles in profile '{}': {}".format(name, exc))

            profiles[name] = {'definition': definition}

        return profiles

    def _get_profiles_mapping(self):
        # type: () -> Dict[str, str]
        """
        Get the mapping from sysObjectID to profile.
        """
        profiles_by_oid = {}  # type: Dict[str, str]
        for name, profile in self.profiles.items():
            sys_object_oids = profile['definition'].get('sysobjectid')
            if sys_object_oids is None:
                continue
            if isinstance(sys_object_oids, str):
                sys_object_oids = [sys_object_oids]
            for sys_object_oid in sys_object_oids:
                profile_match = profiles_by_oid.get(sys_object_oid)
                if profile_match:
                    raise ConfigurationError(
                        "Profile {} has the same sysObjectID ({}) as {}".format(name, sys_object_oid, profile_match)
                    )
                else:
                    profiles_by_oid[sys_object_oid] = name
        return profiles_by_oid

    def _build_config(self, instance):
        # type: (dict) -> InstanceConfig
        loader = MIBLoader.shared_instance() if self.optimize_mib_memory_usage else MIBLoader()

        return InstanceConfig(
            instance,
            global_metrics=self.init_config.get('global_metrics', []),
            mibs_path=self.mibs_path,
            profiles=self.profiles,
            profiles_by_oid=self.profiles_by_oid,
            loader=loader,
            logger=self.log,
        )

    def _build_autodiscovery_config(self, source_instance, ip_address):
        # type: (dict, str) -> InstanceConfig
        instance = copy.deepcopy(source_instance)
        network_address = instance.pop('network_address')
        instance['ip_address'] = ip_address

        instance.setdefault('tags', [])
        instance['tags'].append('autodiscovery_subnet:{}'.format(network_address))

        return self._build_config(instance)

    def _get_instance_name(self, instance):
        # type: (Dict[str, Any]) -> Optional[str]
        name = instance.get('name')
        if name:
            return name

        ip = instance.get('ip_address')  # type: Optional[str]
        port = instance.get('port')  # type: Optional[int]

        if ip and port:
            return '{host}:{port}'.format(host=ip, port=port)
        elif ip:
            return ip
        else:
            return None

    def fetch_results(
        self, config  # type: InstanceConfig
    ):
        # type: (...) -> Tuple[Dict[str, Dict[Tuple[str, ...], Any]], List[OID], Optional[str]]
        """
        Perform a snmpwalk on the domain specified by the oids, on the device
        configured in instance.

        Returns a dictionary:
        dict[oid/metric_name][row index] = value
        In case of scalar objects, the row index is just 0
        """
        results = defaultdict(dict)  # type: DefaultDict[str, Dict[Tuple[str, ...], Any]]
        enforce_constraints = config.enforce_constraints

        all_binds, error = self.fetch_oids(
            config, config.oid_config.scalar_oids, config.oid_config.next_oids, enforce_constraints=enforce_constraints
        )
        for oid in config.oid_config.bulk_oids:
            try:
                self.log.debug('Running SNMP command getBulk on OID %s', oid)
                binds = snmp_bulk(
                    config,
                    oid.as_object_type(),
                    self._NON_REPEATERS,
                    self._MAX_REPETITIONS,
                    enforce_constraints,
                    self.ignore_nonincreasing_oid,
                )
                all_binds.extend(binds)
            except (PySnmpError, CheckException) as e:
                message = 'Failed to collect some metrics: {}'.format(e)
                if not error:
                    error = message
                self.warning(message)

        scalar_oids = []
        for result_oid, value in all_binds:
            oid = OID(result_oid)
            scalar_oids.append(oid)
            match = config.resolve_oid(oid)
            results[match.name][match.indexes] = value
        self.log.debug('Raw results: %s', OIDPrinter(results, with_values=False))
        # Freeze the result
        results.default_factory = None  # type: ignore
        return results, scalar_oids, error

    def fetch_oids(self, config, scalar_oids, next_oids, enforce_constraints):
        # type: (InstanceConfig, List[OID], List[OID], bool) -> Tuple[List[Any], Optional[str]]
        # UPDATE: We used to perform only a snmpgetnext command to fetch metric values.
        # It returns the wrong value when the OID passed is referring to a specific leaf.
        # For example:
        # snmpgetnext -v2c -c public localhost:11111 1.3.6.1.2.1.25.4.2.1.7.222
        # iso.3.6.1.2.1.25.4.2.1.7.224 = INTEGER: 2
        # SOLUTION: perform a snmpget command and fallback with snmpgetnext if not found
        error = None
        scalar_oids = [oid.as_object_type() for oid in scalar_oids]
        next_oids = [oid.as_object_type() for oid in next_oids]
        all_binds = []

        for oids_batch in batches(scalar_oids, size=self.oid_batch_size):
            try:
                self.log.debug('Running SNMP command get on OIDS: %s', OIDPrinter(oids_batch, with_values=False))

                var_binds = snmp_get(config, oids_batch, lookup_mib=enforce_constraints)
                self.log.debug('Returned vars: %s', OIDPrinter(var_binds, with_values=True))

                missing_results = []

                for var in var_binds:
                    result_oid, value = var
                    if reply_invalid(value):
                        oid_tuple = result_oid.asTuple()
                        missing_results.append(ObjectType(ObjectIdentity(oid_tuple)))
                    else:
                        all_binds.append(var)

                if missing_results:
                    # If we didn't catch the metric using snmpget, try snmpnext
                    next_oids.extend(missing_results)

            except (PySnmpError, CheckException) as e:
                message = 'Failed to collect some metrics: {}'.format(e)
                if not error:
                    error = message
                self.warning(message)

        for oids_batch in batches(next_oids, size=self.oid_batch_size):
            try:
                self.log.debug('Running SNMP command getNext on OIDS: %s', OIDPrinter(oids_batch, with_values=False))
                binds = list(
                    snmp_getnext(
                        config,
                        oids_batch,
                        lookup_mib=enforce_constraints,
                        ignore_nonincreasing_oid=self.ignore_nonincreasing_oid,
                    )
                )
                self.log.debug('Returned vars: %s', OIDPrinter(binds, with_values=True))
                all_binds.extend(binds)

            except (PySnmpError, CheckException) as e:
                message = 'Failed to collect some metrics: {}'.format(e)
                if not error:
                    error = message
                self.warning(message)

        return all_binds, error

    def fetch_sysobject_oid(self, config):
        # type: (InstanceConfig) -> str
        """Return the sysObjectID of the instance."""
        # Reference sysObjectID directly, see http://oidref.com/1.3.6.1.2.1.1.2
        oid = ObjectType(ObjectIdentity((1, 3, 6, 1, 2, 1, 1, 2, 0)))
        self.log.debug('Running SNMP command on OID: %s', OIDPrinter((oid,), with_values=False))
        var_binds = snmp_get(config, [oid], lookup_mib=False)
        self.log.debug('Returned vars: %s', OIDPrinter(var_binds, with_values=True))
        return var_binds[0][1].prettyPrint()

    def _profile_for_sysobject_oid(self, sys_object_oid):
        # type: (str) -> str
        """
        Return the most specific profile that matches the given sysObjectID.
        """
        matched_profiles_by_oid = {
            oid: self.profiles_by_oid[oid] for oid in self.profiles_by_oid if fnmatch.fnmatch(sys_object_oid, oid)
        }

        if not matched_profiles_by_oid:
            raise ConfigurationError('No profile matching sysObjectID {}'.format(sys_object_oid))

        oid = max(matched_profiles_by_oid.keys(), key=lambda oid: oid_pattern_specificity(oid))

        return matched_profiles_by_oid[oid]

    def _start_discovery(self):
        # type: () -> None
        cache = read_persistent_cache(self.check_id)
        if cache:
            hosts = json.loads(cache)
            for host in hosts:
                try:
                    ipaddress.ip_address(host)
                except ValueError:
                    write_persistent_cache(self.check_id, json.dumps([]))
                    break
                self._config.discovered_instances[host] = self._build_autodiscovery_config(self.instance, host)

        raw_discovery_interval = self._config.instance.get('discovery_interval', 3600)
        try:
            discovery_interval = float(raw_discovery_interval)
        except (ValueError, TypeError):
            message = 'discovery_interval could not be parsed as a number: {!r}'.format(raw_discovery_interval)
            raise ConfigurationError(message)

        # Pass a weakref to the discovery function to not have a reference cycle
        self._thread = self._thread_factory(
            target=discover_instances, args=(self._config, discovery_interval, weakref.ref(self)), name=self.name
        )
        self._thread.daemon = True
        self._thread.start()
        self._executor = futures.ThreadPoolExecutor(max_workers=self._config.workers)

    def check(self, instance):
        # type: (Dict[str, Any]) -> None
        config = self._config
        if config.ip_network:
            if self._thread is None:
                self._start_discovery()

            executor = self._executor
            if executor is None:
                raise RuntimeError("Expected executor be set")

            sent = []
            for host, discovered in list(config.discovered_instances.items()):
                future = executor.submit(self._check_device, discovered)
                sent.append(future)
                future.add_done_callback(functools.partial(self._on_check_device_done, host))
            futures.wait(sent)

            tags = ['network:{}'.format(config.ip_network)]
            tags.extend(config.tags)
            self.gauge('snmp.discovered_devices_count', len(config.discovered_instances), tags=tags)
        else:
            self._check_device(config)

    def _on_check_device_done(self, host, future):
        # type: (str, futures.Future) -> None
        config = self._config
        if future.result():
            config.failing_instances[host] += 1
            if config.failing_instances[host] >= config.allowed_failures:
                # Remove it from discovered instances, we'll re-discover it later if it reappears
                config.discovered_instances.pop(host)
                # Reset the failure counter as well
                config.failing_instances.pop(host)
        else:
            # Reset the counter if not's failing
            config.failing_instances.pop(host, None)

    def _check_device(self, config):
        # type: (InstanceConfig) -> Optional[str]
        # Reset errors
        if config.device is None:
            raise RuntimeError('No device set')  # pragma: no cover

        instance = config.instance
        error = results = None
        tags = config.tags
        if config.oid_config.should_reset():
            config.oid_config.reset()
        try:
            if not config.oid_config.has_oids():
                sys_object_oid = self.fetch_sysobject_oid(config)
                profile = self._profile_for_sysobject_oid(sys_object_oid)
                config.refresh_with_profile(self.profiles[profile])
                config.add_profile_tag(profile)

            if config.oid_config.has_oids():
                self.log.debug('Querying %s', config.device)
                config.add_uptime_metric()
                results, scalar_oids, error = self.fetch_results(config)
                config.oid_config.update_scalar_oids(scalar_oids)
                tags = self.extract_metric_tags(config.parsed_metric_tags, results)
                tags.extend(config.tags)
                self.report_metrics(config.parsed_metrics, results, tags)
        except CheckException as e:
            error = str(e)
            self.warning(error)
        except Exception as e:
            if not error:
                error = 'Failed to collect metrics for {} - {}'.format(self._get_instance_name(instance), e)
            self.log.debug(error, exc_info=True)
            self.warning(error)
        finally:
            # At this point, `tags` might include some extra tags added in try clause

            # Sending `snmp.devices_monitored` with value 1 will allow users to count devices
            # by using `sum by {X}` queries in UI. X being a tag like `autodiscovery_subnet`, `snmp_profile`, etc
            self.gauge('snmp.devices_monitored', 1, tags=tags)

            # Report service checks
            status = self.OK
            if error:
                status = self.CRITICAL
                if results:
                    status = self.WARNING
            self.service_check(self.SC_STATUS, status, tags=tags, message=error)
        return error

    def extract_metric_tags(self, metric_tags, results):
        # type: (List[SymbolTag], Dict[str, dict]) -> List[str]
        extracted_tags = []  # type: List[str]
        for tag in metric_tags:
            if tag.symbol not in results:
                self.log.debug('Ignoring tag %s', tag.symbol)
                continue
            tag_values = list(results[tag.symbol].values())
            if len(tag_values) > 1:
                raise CheckException(
                    'You are trying to use a table column (OID `{}`) as a metric tag. This is not supported as '
                    '`metric_tags` can only refer to scalar OIDs.'.format(tag.symbol)
                )
            try:
                extracted_tags.extend(tag.parsed_metric_tag.matched_tags(tag_values[0]))
            except re.error as e:
                self.log.debug('Failed to match %s for %s: %s', tag_values[0], tag.symbol, e)
        return extracted_tags

    def report_metrics(
        self,
        metrics,  # type: List[ParsedMetric]
        results,  # type: Dict[str, Dict[Tuple[str, ...], Any]]
        tags,  # type: List[str]
    ):
        # type: (...) -> None
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
                    self.submit_metric(name, val, metric.forced_type, metric_tags, metric.options)
            else:
                result = list(results[name].items())
                if len(result) > 1:
                    self.log.warning('Several rows corresponding while the metric is supposed to be a scalar')
                    if metric.enforce_scalar:
                        # For backward compatibility reason, we publish the first value for OID.
                        continue
                val = result[0][1]
                metric_tags = tags + metric.tags
                self.submit_metric(name, val, metric.forced_type, metric_tags, metric.options)

    def get_index_tags(
        self,
        index,  # type: Tuple[str, ...]
        results,  # type: Dict[str, dict]
        index_tags,  # type: List[IndexTag]
        column_tags,  # type: List[ColumnTag]
    ):
        # type: (...) -> List[str]
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
        tags = []  # type: List[str]

        for index_tag in index_tags:
            raw_index_value = index_tag.index
            try:
                value = index[raw_index_value - 1]
            except IndexError:
                self.log.warning('Not enough indexes, skipping index %s', raw_index_value)
                continue
            tags.extend(index_tag.parsed_metric_tag.matched_tags(value))

        for column_tag in column_tags:
            raw_column_value = column_tag.column
            try:
                column_value = results[raw_column_value][index]
            except KeyError:
                self.log.warning('Column %s not present in the table, skipping this tag', raw_column_value)
                continue
            if reply_invalid(column_value):
                self.log.warning("Can't deduct tag from column %s", column_tag.column)
                continue
            value = column_value.prettyPrint()
            tags.extend(column_tag.parsed_metric_tag.matched_tags(value))
        return tags

    def monotonic_count_and_rate(self, metric, value, tags):
        # type: (str, Any, List[str]) -> None
        """Specific submission method which sends a metric both as a monotonic cound and a rate."""
        self.monotonic_count(metric, value, tags=tags)
        self.rate("{}.rate".format(metric), value, tags=tags)

    def submit_metric(self, name, snmp_value, forced_type, tags, options):
        # type: (str, Any, Optional[str], List[str], dict) -> None
        """
        Convert the values reported as pysnmp-Managed Objects to values and
        report them to the aggregator.
        """
        try:
            self._do_submit_metric(name, snmp_value, forced_type, tags, options)
        except Exception as e:
            msg = (
                'Unable to submit metric `{}` with '
                'value=`{}` ({}), forced_type=`{}`, tags=`{}`, options=`{}`: {}'.format(
                    name, snmp_value, type(snmp_value), forced_type, tags, options, e
                )
            )
            self.log.warning(msg)
            self.log.debug(msg, exc_info=True)

    def _do_submit_metric(self, name, snmp_value, forced_type, tags, options):
        # type: (str, Any, Optional[str], List[str], dict) -> None

        if reply_invalid(snmp_value):
            # Metrics not present in the queried object
            self.log.warning('No such Mib available: %s', name)
            return

        if 'metric_suffix' in options:
            metric_name = self.normalize('{}.{}'.format(name, options['metric_suffix']), prefix='snmp')
        else:
            metric_name = self.normalize(name, prefix='snmp')

        if forced_type is not None:
            metric = as_metric_with_forced_type(snmp_value, forced_type, options)
        else:
            metric = as_metric_with_inferred_type(snmp_value)

        if metric is None:
            raise RuntimeError('Unsupported metric type {} for {}'.format(type(snmp_value), metric_name))

        submit_func = getattr(self, metric['type'])
        submit_func(metric_name, metric['value'], tags=tags)
