# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import win32wnet
from six import iteritems

from ... import AgentCheck, is_affirmative
from ...utils.containers import hash_mutable

try:
    from .winpdh import WinPDHCounter, DATA_TYPE_INT, DATA_TYPE_DOUBLE
except ImportError:
    from .winpdh_stub import WinPDHCounter, DATA_TYPE_INT, DATA_TYPE_DOUBLE


RESOURCETYPE_ANY = 0
DEFAULT_SHARE = 'c$'

int_types = ["int", "long", "uint"]

double_types = ["double", "float"]


class PDHBaseCheck(AgentCheck):
    """
    PDH based check.  check.

    Windows only.
    """

    def __init__(self, name, init_config, agentConfig, instances, counter_list):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self._missing_counters = {}
        self._metrics = {}
        self._tags = {}
        key = None

        try:
            for instance in instances:
                key = hash_mutable(instance)

                cfg_tags = instance.get('tags')
                if cfg_tags is not None:
                    if not isinstance(cfg_tags, list):
                        self.log.error("Tags must be configured as a list")
                        raise ValueError("Tags must be type list, not %s" % str(type(cfg_tags)))
                    self._tags[key] = list(cfg_tags)

                remote_machine = None
                host = instance.get('host')
                self._metrics[key] = []
                if host is not None and host != ".":
                    try:
                        remote_machine = host

                        username = instance.get('username')
                        password = instance.get('password')
                        nr = self._get_netresource(remote_machine)
                        win32wnet.WNetAddConnection2(nr, password, username, 0)

                    except Exception as e:
                        self.log.error("Failed to make remote connection %s", str(e))
                        return

                # counter_data_types allows the precision with which counters are queried
                # to be configured on a per-metric basis. In the metric instance, precision
                # should be specified as
                # counter_data_types:
                # - iis.httpd_request_method.get,int
                # - iis.net.bytes_rcvd,float
                #
                # the above would query the counter associated with iis.httpd_request_method.get
                # as an integer (LONG) and iis.net.bytes_rcvd as a double
                datatypes = {}
                precisions = instance.get('counter_data_types')
                if precisions is not None:
                    if not isinstance(precisions, list):
                        self.log.warning("incorrect type for counter_data_type %s", str(precisions))
                    else:
                        for p in precisions:
                            k, v = p.split(",")
                            v = v.lower().strip()
                            if v in int_types:
                                self.log.info("Setting datatype for %s to integer", k)
                                datatypes[k] = DATA_TYPE_INT
                            elif v in double_types:
                                self.log.info("Setting datatype for %s to double", k)
                                datatypes[k] = DATA_TYPE_DOUBLE
                            else:
                                self.log.warning("Unknown data type %s", str(v))

                self._make_counters(key, (counter_list, (datatypes, remote_machine, False, 'entry')))

                # get any additional metrics in the instance
                addl_metrics = instance.get('additional_metrics')
                if addl_metrics is not None:
                    self._make_counters(
                        key, (addl_metrics, (datatypes, remote_machine, True, 'additional metric entry'))
                    )

        except Exception as e:
            self.log.debug("Exception in PDH init: %s", str(e))
            raise

        if key is None or not self._metrics.get(key):
            raise AttributeError('No valid counters to collect')

    def _get_netresource(self, remote_machine):
        # To connect you have to use the name of the server followed by an optional administrative share.
        # Administrative shares are hidden network shares created that allow system administrators to have remote access
        # to every disk volume on a network-connected system.
        # These shares may not be permanently deleted but may be disabled.
        # Administrative shares cannot be accessed by users without administrative privileges.
        #
        # This page explains how to enable them: https://www.wintips.org/how-to-enable-admin-shares-windows-7/
        #
        # The administrative share can be:
        # * A disk volume like c$
        # * admin$: The folder in which Windows is installed
        # * fax$: The folder in which faxed pages and cover pages are cached
        # * ipc$: Area used for interprocess communication and is not part of the file system.
        # * print$: Virtual folder that contains a representation of the installed printers
        # * Domain controller shares: Windows creates two domain controller specific shares called sysvol and netlogon
        #   which do not have $ appended to their names.
        # * Empty string: No admin share specified
        administrative_share = self.instance.get('admin_share', DEFAULT_SHARE)

        nr = win32wnet.NETRESOURCE()

        # Specifies the network resource to connect to.
        nr.lpRemoteName = r"\\{}\{}".format(remote_machine, administrative_share).rstrip('\\')

        # The type of network resource to connect to.
        #
        # Although this member is required, its information may be ignored by the network service provider.
        nr.dwType = RESOURCETYPE_ANY

        # Specifies the name of a local device to redirect, such as "F:" or "LPT1".
        # If the string is empty, NULL, it connects to the network resource without redirecting a local device.
        nr.lpLocalName = None

        return nr

    def check(self, instance):
        self.log.debug("PDHBaseCheck: check()")
        key = hash_mutable(instance)
        refresh_counters = is_affirmative(instance.get('refresh_counters', True))

        if refresh_counters:
            for counter, values in list(iteritems(self._missing_counters)):
                self._make_counters(key, ([counter], values))

        for inst_name, dd_name, metric_func, counter in self._metrics[key]:
            try:
                if refresh_counters:
                    counter.collect_counters()
                vals = counter.get_all_values()
                for instance_name, val in iteritems(vals):
                    tags = []
                    if key in self._tags:
                        tags = list(self._tags[key])

                    if not counter.is_single_instance():
                        tag = "instance:%s" % instance_name
                        tags.append(tag)
                    metric_func(dd_name, val, tags)
            except Exception as e:
                # don't give up on all of the metrics because one failed
                self.log.error("Failed to get data for %s %s: %s", inst_name, dd_name, str(e))

    def _make_counters(self, key, counter_data):
        counter_list, (datatypes, remote_machine, check_instance, message) = counter_data

        # list of the metrics. Each entry is itself an entry,
        # which is the pdh name, datadog metric name, type, and the
        # pdh counter object
        for counterset, inst_name, counter_name, dd_name, mtype in counter_list:
            if check_instance and self._no_instance(inst_name):
                inst_name = None

            m = getattr(self, mtype.lower())
            precision = datatypes.get(dd_name)

            try:
                obj = WinPDHCounter(
                    counterset, counter_name, self.log, inst_name, machine_name=remote_machine, precision=precision
                )
            except Exception as e:
                self.log.debug(
                    'Could not create counter %s\\%s due to %s, will not report %s.',
                    counterset,
                    counter_name,
                    e,
                    dd_name,
                )
                self._missing_counters[(counterset, inst_name, counter_name, dd_name, mtype)] = (
                    datatypes,
                    remote_machine,
                    check_instance,
                    message,
                )
                continue
            else:
                self._missing_counters.pop((counterset, inst_name, counter_name, dd_name, mtype), None)

            entry = [inst_name, dd_name, m, obj]
            self.log.debug('%s: %s', message, entry)
            self._metrics[key].append(entry)

    @classmethod
    def _no_instance(cls, inst_name):
        return inst_name.lower() == 'none' or len(inst_name) == 0 or inst_name == '*' or inst_name.lower() == 'all'
