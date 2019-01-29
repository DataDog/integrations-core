# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from six import iteritems

from collections import defaultdict

import pysnmp.proto.rfc1902 as snmp_type
from pysnmp.smi import builder, view
from pysnmp.smi.exval import noSuchInstance, noSuchObject
from pysnmp.error import PySnmpError
from pyasn1.type.univ import OctetString
from pysnmp import hlapi

from datadog_checks.checks.network import NetworkCheck, Status
from datadog_checks.config import _is_affirmative

# Additional types that are not part of the SNMP protocol. cf RFC 2856
(CounterBasedGauge64, ZeroBasedCounter64) = builder.MibBuilder().importSymbols(
    "HCNUM-TC",
    "CounterBasedGauge64",
    "ZeroBasedCounter64")

# Metric type that we support
SNMP_COUNTERS = frozenset([
    snmp_type.Counter32.__name__,
    snmp_type.Counter64.__name__,
    ZeroBasedCounter64.__name__])

SNMP_GAUGES = frozenset([
    snmp_type.Gauge32.__name__,
    snmp_type.Unsigned32.__name__,
    CounterBasedGauge64.__name__,
    snmp_type.Integer.__name__,
    snmp_type.Integer32.__name__])

DEFAULT_OID_BATCH_SIZE = 10


def reply_invalid(oid):
    return noSuchInstance.isSameTypeWith(oid) or \
        noSuchObject.isSameTypeWith(oid)


class SnmpCheck(NetworkCheck):

    SOURCE_TYPE_NAME = 'system'
    # pysnmp default values
    DEFAULT_RETRIES = 5
    DEFAULT_TIMEOUT = 1
    SC_STATUS = 'snmp.can_check'

    def __init__(self, name, init_config, agentConfig, instances):
        for instance in instances:
            if 'name' not in instance:
                instance['name'] = self._get_instance_key(instance)

        # Set OID batch size
        self.oid_batch_size = int(init_config.get("oid_batch_size", DEFAULT_OID_BATCH_SIZE))

        # Load Custom MIB directory
        self.mibs_path = None
        self.ignore_nonincreasing_oid = False
        if init_config is not None:
            self.mibs_path = init_config.get("mibs_folder")
            self.ignore_nonincreasing_oid = _is_affirmative(
                init_config.get("ignore_nonincreasing_oid", False))

        NetworkCheck.__init__(self, name, init_config, agentConfig, instances)

    def _load_conf(self, instance):
        tags = instance.get("tags", [])
        ip_address = instance["ip_address"]
        metrics = instance.get('metrics', [])
        timeout = int(instance.get('timeout', self.DEFAULT_TIMEOUT))
        retries = int(instance.get('retries', self.DEFAULT_RETRIES))
        enforce_constraints = _is_affirmative(instance.get('enforce_mib_constraints', True))
        snmp_engine, mib_view_controller = self.create_snmp_engine(self.mibs_path)

        return snmp_engine, mib_view_controller, ip_address, tags, metrics, timeout, retries, enforce_constraints

    def _get_instance_key(self, instance):
        key = instance.get('name', None)
        if key:
            return key

        host = instance.get('host', None)
        ip = instance.get('ip_address', None)
        port = instance.get('port', None)
        if host and port:
            key = "{host}:{port}".format(host=host, port=port)
        elif ip and port:
            key = "{host}:{port}".format(host=ip, port=port)
        elif host:
            key = host
        elif ip:
            key = ip

        return key

    def create_snmp_engine(self, mibs_path):
        '''
        Create a command generator to perform all the snmp query.
        If mibs_path is not None, load the mibs present in the custom mibs
        folder. (Need to be in pysnmp format)
        '''
        snmp_engine = hlapi.SnmpEngine()
        mib_builder = snmp_engine.getMibBuilder()
        if mibs_path is not None:
            mib_builder.addMibSources(builder.DirMibSource(mibs_path))

        mib_view_controller = view.MibViewController(mib_builder)

        return snmp_engine, mib_view_controller

    @classmethod
    def get_auth_data(cls, instance):
        '''
        Generate a Security Parameters object based on the instance's
        configuration.
        See http://pysnmp.sourceforge.net/docs/current/security-configuration.html
        '''
        if "community_string" in instance:
            # SNMP v1 - SNMP v2

            # See http://pysnmp.sourceforge.net/docs/current/security-configuration.html
            if int(instance.get("snmp_version", 2)) == 1:
                return hlapi.CommunityData(instance['community_string'], mpModel=0)
            return hlapi.CommunityData(instance['community_string'], mpModel=1)

        elif "user" in instance:
            # SNMP v3
            user = instance["user"]
            auth_key = None
            priv_key = None
            auth_protocol = None
            priv_protocol = None
            if "authKey" in instance:
                auth_key = instance["authKey"]
                auth_protocol = hlapi.usmHMACMD5AuthProtocol
            if "privKey" in instance:
                priv_key = instance["privKey"]
                auth_protocol = hlapi.usmHMACMD5AuthProtocol
                priv_protocol = hlapi.usmDESPrivProtocol
            if "authProtocol" in instance:
                auth_protocol = getattr(hlapi, instance["authProtocol"])
            if "privProtocol" in instance:
                priv_protocol = getattr(hlapi, instance["privProtocol"])
            return hlapi.UsmUserData(user, auth_key, priv_key, auth_protocol, priv_protocol)
        else:
            raise Exception("An authentication method needs to be provided")

    @classmethod
    def get_context_data(cls, instance):
        '''
        Generate a Context Parameters object based on the instance's
        configuration.
        We do not use the hlapi currently, but the rfc3413.oneliner.cmdgen
        accepts Context Engine Id (always None for now) and Context Name parameters.
        '''

        context_engine_id = None
        context_name = ''

        if "user" in instance:
            if 'context_engine_id' in instance:
                context_engine_id = OctetString(instance['context_engine_id'])
            if 'context_name' in instance:
                context_name = instance['context_name']

        return context_engine_id, context_name

    @classmethod
    def get_transport_target(cls, instance, timeout, retries):
        '''
        Generate a Transport target object based on the instance's configuration
        '''
        if "ip_address" not in instance:
            raise Exception("An IP address needs to be specified")
        ip_address = instance["ip_address"]
        port = int(instance.get("port", 161))  # Default SNMP port
        return hlapi.UdpTransportTarget((ip_address, port), timeout=timeout, retries=retries)

    def raise_on_error_indication(self, error_indication, instance):
        if error_indication:
            message = "{} for instance {}".format(error_indication, instance["ip_address"])
            instance["service_check_error"] = message
            raise Exception(message)

    def check_table(self, instance, snmp_engine, mib_view_controller, oids, lookup_names,
                    timeout, retries, enforce_constraints=False, mibs_to_load=None):
        '''
        Perform a snmpwalk on the domain specified by the oids, on the device
        configured in instance.
        lookup_names is a boolean to specify whether or not to use the mibs to
        resolve the name and values.

        Returns a dictionary:
        dict[oid/metric_name][row index] = value
        In case of scalar objects, the row index is just 0
        '''
        # UPDATE: We used to perform only a snmpgetnext command to fetch metric values.
        # It returns the wrong value when the OID passeed is referring to a specific leaf.
        # For example:
        # snmpgetnext -v2c -c public localhost:11111 1.3.6.1.2.1.25.4.2.1.7.222
        # iso.3.6.1.2.1.25.4.2.1.7.224 = INTEGER: 2
        # SOLUTION: perform a snmpget command and fallback with snmpgetnext if not found

        # Set aliases for snmpget and snmpgetnext with logging
        transport_target = self.get_transport_target(instance, timeout, retries)
        auth_data = self.get_auth_data(instance)
        context_engine_id, context_name = self.get_context_data(instance)

        first_oid = 0
        all_binds = []
        results = defaultdict(dict)

        while first_oid < len(oids):
            try:
                # Start with snmpget command
                oids_batch = oids[first_oid:first_oid + self.oid_batch_size]
                self.log.debug("Running SNMP command get on OIDS {}".format(oids_batch))
                error_indication, error_status, error_index, var_binds = next(hlapi.getCmd(
                    snmp_engine,
                    auth_data,
                    transport_target,
                    hlapi.ContextData(context_engine_id, context_name),
                    *(oids_batch),
                    lookupMib=enforce_constraints
                ))
                self.log.debug("Returned vars: {}".format(var_binds))

                # Raise on error_indication
                self.raise_on_error_indication(error_indication, instance)

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
                    self.log.debug("Running SNMP command getNext on OIDS {}".format(missing_results))
                    for error_indication, error_status, error_index, var_binds_table in hlapi.nextCmd(
                        snmp_engine,
                        auth_data,
                        transport_target,
                        hlapi.ContextData(context_engine_id, context_name),
                        *missing_results,
                        lookupMib=enforce_constraints,
                        ignoreNonIncreasingOid=self.ignore_nonincreasing_oid,
                        lexicographicMode=False  # Don't walk through the entire MIB, stop at end of table
                    ):

                        self.log.debug("Returned vars: {}".format(var_binds_table))
                        # Raise on error_indication
                        self.raise_on_error_indication(error_indication, instance)

                        if error_status:
                            message = "{} for instance {}".format(error_status.prettyPrint(), instance["ip_address"])
                            instance["service_check_error"] = message

                            # submit CRITICAL service check if we can't connect to device
                            if 'unknownUserName' in message:
                                instance["service_check_severity"] = Status.CRITICAL
                                self.log.error(message)
                            else:
                                self.warning(message)

                        for table_row in var_binds_table:
                            complete_results.append(table_row)

                all_binds.extend(complete_results)

            except PySnmpError as e:
                if "service_check_error" not in instance:
                    instance["service_check_error"] = "Fail to collect some metrics: {}".format(e)
                if "service_check_severity" not in instance:
                    instance["service_check_severity"] = Status.CRITICAL
                self.warning("Fail to collect some metrics: {}".format(e))

            # if we fail move onto next batch
            first_oid = first_oid + self.oid_batch_size

        # if we've collected some variables, it's not that bad.
        if "service_check_severity" in instance and len(all_binds):
            instance["service_check_severity"] = Status.WARNING

        for result_oid, value in all_binds:
            if lookup_names:
                if not enforce_constraints:
                    # if enforce_constraints is false, then MIB resolution has not been done yet
                    # so we need to do it manually. We have to specify the mibs that we will need
                    # to resolve the name.
                    oid_to_resolve = hlapi.ObjectIdentity(result_oid.asTuple()).loadMibs(*mibs_to_load)
                    result_oid = oid_to_resolve.resolveWithMib(mib_view_controller)
                _, metric, indexes = result_oid.getMibSymbol()
                results[metric][indexes] = value
            else:
                oid = result_oid.asTuple()
                matching = ".".join([str(i) for i in oid])
                results[matching] = value
        self.log.debug("Raw results: {}".format(results))
        return results

    def _check(self, instance):
        '''
        Perform two series of SNMP requests, one for all that have MIB asociated
        and should be looked up and one for those specified by oids
        '''

        (snmp_engine, mib_view_controller, ip_address,
         tags, metrics, timeout, retries, enforce_constraints) = self._load_conf(instance)

        if not metrics:
            raise Exception('Metrics list must contain at least one metric')

        tags += ['snmp_device:{}'.format(ip_address)]

        table_oids = []
        raw_oids = []
        mibs_to_load = set()

        # Check the metrics completely defined
        for metric in metrics:
            if 'MIB' in metric:
                try:
                    assert "table" in metric or "symbol" in metric
                    if not enforce_constraints:
                        # We need this only if we don't enforce constraints to be able to lookup MIBs manually
                        mibs_to_load.add(metric["MIB"])
                    to_query = metric.get("table", metric.get("symbol"))
                    table_oids.append(hlapi.ObjectType(hlapi.ObjectIdentity(metric["MIB"], to_query)))
                except Exception as e:
                    self.log.warning("Can't generate MIB object for variable : %s\n"
                                     "Exception: %s", metric, e)
            elif 'OID' in metric:
                raw_oids.append(hlapi.ObjectType(hlapi.ObjectIdentity(metric['OID'])))
            else:
                raise Exception('Unsupported metric in config file: {}'.format(metric))
        try:
            if table_oids:
                self.log.debug("Querying device %s for %s oids", ip_address, len(table_oids))
                table_results = self.check_table(
                    instance, snmp_engine, mib_view_controller, table_oids, True, timeout, retries,
                    enforce_constraints=enforce_constraints, mibs_to_load=mibs_to_load
                )
                self.report_table_metrics(metrics, table_results, tags)

            if raw_oids:
                self.log.debug("Querying device %s for %s oids", ip_address, len(raw_oids))
                raw_results = self.check_table(
                    instance, snmp_engine, mib_view_controller, raw_oids, False, timeout, retries,
                    enforce_constraints=False
                )
                self.report_raw_metrics(metrics, raw_results, tags)
        except Exception as e:
            if "service_check_error" not in instance:
                instance["service_check_error"] = "Fail to collect metrics for {} - {}".format(instance['name'], e)
            self.warning(instance["service_check_error"])
        finally:
            # Report service checks
            if "service_check_error" in instance:
                status = Status.DOWN
                if "service_check_severity" in instance:
                    status = instance["service_check_severity"]
                return [(self.SC_STATUS, status, instance["service_check_error"])]

            return [(self.SC_STATUS, Status.UP, None)]

    def report_as_service_check(self, sc_name, status, instance, msg=None):
        sc_tags = ['snmp_device:{}'.format(instance["ip_address"])]
        custom_tags = instance.get('tags', [])
        tags = sc_tags + custom_tags

        self.service_check(sc_name,
                           NetworkCheck.STATUS_TO_SERVICE_CHECK[status],
                           tags=tags,
                           message=msg
                           )

    def report_raw_metrics(self, metrics, results, tags):
        '''
        For all the metrics that are specified as oid,
        the conf oid is going to exactly match or be a prefix of the oid sent back by the device
        Use the instance configuration to find the name to give to the metric

        Submit the results to the aggregator.
        '''

        for metric in metrics:
            forced_type = metric.get('forced_type')
            if 'OID' in metric:
                queried_oid = metric['OID']
                if queried_oid in results:
                    value = results[queried_oid]
                else:
                    for oid in results:
                        if oid.startswith(queried_oid):
                            value = results[oid]
                            break
                    else:
                        self.log.warning("No matching results found for oid %s",
                                         queried_oid)
                        continue
                name = metric.get('name', 'unnamed_metric')
                metric_tags = tags
                if metric.get('metric_tags'):
                    metric_tags = metric_tags + metric.get('metric_tags')
                self.submit_metric(name, value, forced_type, metric_tags)

    def report_table_metrics(self, metrics, results, tags):
        '''
        For each of the metrics specified as needing to be resolved with mib,
        gather the tags requested in the instance conf for each row.

        Submit the results to the aggregator.
        '''

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
                        self.log.warning("No indication on what value to use for this tag")

                for value_to_collect in metric.get("symbols", []):
                    for index, val in iteritems(results[value_to_collect]):
                        metric_tags = tags + self.get_index_tags(index, results,
                                                                 index_based_tags,
                                                                 column_based_tags)
                        self.submit_metric(value_to_collect, val, forced_type, metric_tags)

            elif 'symbol' in metric:
                name = metric['symbol']
                result = list(results[name].items())
                if len(result) > 1:
                    self.log.warning("Several rows corresponding while the metric is supposed to be a scalar")
                    continue
                val = result[0][1]
                metric_tags = tags
                if metric.get('metric_tags'):
                    metric_tags = metric_tags + metric.get('metric_tags')
                self.submit_metric(name, val, forced_type, metric_tags)
            elif 'OID' in metric:
                pass  # This one is already handled by the other batch of requests
            else:
                raise Exception('Unsupported metric in config file: {}'.format(metric))

    def get_index_tags(self, index, results, index_tags, column_tags):
        '''
        Gather the tags for this row of the table (index) based on the
        results (all the results from the query).
        index_tags and column_tags are the tags to gather.
         - Those specified in index_tags contain the tag_group name and the
           index of the value we want to extract from the index tuple.
           cf. 1 for ipVersion in the IP-MIB::ipSystemStatsTable for example
         - Those specified in column_tags contain the name of a column, which
           could be a potential result, to use as a tage
           cf. ifDescr in the IF-MIB::ifTable for example
        '''
        tags = []
        for idx_tag in index_tags:
            tag_group = idx_tag[0]
            try:
                tag_value = index[idx_tag[1] - 1].prettyPrint()
            except IndexError:
                self.log.warning("Not enough indexes, skipping this tag")
                continue
            tags.append("{}:{}".format(tag_group, tag_value))
        for col_tag in column_tags:
            tag_group = col_tag[0]
            try:
                tag_value = results[col_tag[1]][index]
            except KeyError:
                self.log.warning("Column %s not present in the table, skipping this tag", col_tag[1])
                continue
            if reply_invalid(tag_value):
                self.log.warning("Can't deduct tag from column for tag %s",
                                 tag_group)
                continue
            tag_value = tag_value.prettyPrint()
            tags.append("{}:{}".format(tag_group, tag_value))
        return tags

    def submit_metric(self, name, snmp_value, forced_type, tags=None):
        '''
        Convert the values reported as pysnmp-Managed Objects to values and
        report them to the aggregator
        '''
        tags = [] if tags is None else tags
        if reply_invalid(snmp_value):
            # Metrics not present in the queried object
            self.log.warning("No such Mib available: {}".format(name))
            return

        metric_name = self.normalize(name, prefix="snmp")

        if forced_type:
            if forced_type.lower() == "gauge":
                value = int(snmp_value)
                self.gauge(metric_name, value, tags)
            elif forced_type.lower() == "counter":
                value = int(snmp_value)
                self.rate(metric_name, value, tags)
            else:
                self.warning("Invalid forced-type specified: {} in {}".format(forced_type, name))
                raise Exception("Invalid forced-type in config file: {}".format(name))

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

        self.log.warning("Unsupported metric type %s for %s", snmp_class, metric_name)
