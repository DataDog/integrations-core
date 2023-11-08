# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import re
import xml.parsers.expat  # python 2.4 compatible
from collections import defaultdict
from os import geteuid

from packaging.version import Version
from six import PY3, iteritems
from six.moves import filter

from datadog_checks.base import ConfigurationError
from datadog_checks.base.checks import AgentCheck
from datadog_checks.base.utils.subprocess_output import get_subprocess_output

if PY3:
    long = int


class BackendStatus(object):
    HEALTHY = 'healthy'
    SICK = 'sick'
    ALL = (HEALTHY, SICK)

    @classmethod
    def to_check_status(cls, status):
        if status == cls.HEALTHY:
            return AgentCheck.OK
        elif status == cls.SICK:
            return AgentCheck.CRITICAL
        return AgentCheck.UNKNOWN


class Varnish(AgentCheck):
    SERVICE_CHECK_NAME = 'varnish.backend_healthy'
    # Parse metrics from varnishstat.
    VARNISHSTAT_FORMAT_OPTION = {
        "text": "-1",  # version < 3.0.0
        "xml": "-x",  # version >= 3.0.0 < 5.0.0
        "json": "-j",  # version >=5.0.0
    }

    # Output of varnishstat -V : `varnishstat (varnish-4.1.1 revision 66bb824)`
    version_pattern = re.compile(r'(\d+\.\d+\.\d+)')

    def __init__(self, name, init_config, instances):
        super(Varnish, self).__init__(name, init_config, instances)
        self.custom_tags = list(set(self.instance.get('tags', [])))

        # Split the varnishstat command so that additional arguments can be passed in
        # In order to support monitoring a Varnish instance which is running as a Docker
        # container we need to wrap commands (varnishstat, varnishadm) with scripts which
        # perform a docker exec on the running container. This works fine when running a
        # single container on the host but breaks down when attempting to use the auto
        # discovery feature. This change allows for passing in additional parameters to
        # the script (i.e. %%host%%) so that the command is properly formatted and the
        # desired container is queried.
        self.varnishstat_path = self.instance.get('varnishstat', '').split()

        self.varnishadm = self.instance.get("varnishadm", None)
        # Split the varnishadm command so that additional arguments can be passed in
        # In order to support monitoring a Varnish instance which is running as a Docker
        # container we need to wrap commands (varnishstat, varnishadm) with scripts which
        # perform a docker exec on the running container. This works fine when running a
        # single container on the host but breaks down when attempting to use the auto
        # discovery feature. This change allows for passing in additional parameters to
        # the script (i.e. %%host%%) so that the command is properly formatted and the
        # desired container is queried.
        self.varnishadm_path = self.instance.get('varnishadm', '').split()
        self.secretfile_path = self.instance.get('secretfile', '/etc/varnish/secret')

        self.daemon_host = self.instance.get('daemon_host', 'localhost')
        self.daemon_port = self.instance.get('daemon_port', '6082')

        self.name = self.instance.get('name')
        self.metrics_filter = self.instance.get("metrics_filter", [])
        self.tags = self.custom_tags + [u'varnish_name:%s' % (self.name if self.name is not None else 'default')]
        self.check_initializations.append(self.validate_config)

    def validate_config(self):
        if self.instance.get("varnishstat", None) is None:
            raise ConfigurationError("varnishstat is not configured")
        if not isinstance(self.metrics_filter, list):
            raise ConfigurationError("The parameter 'metrics_filter' must be a list")

    # XML parsing bits, a.k.a. Kafka in Code
    def _reset(self):
        self._current_element = ""
        self._current_metric = "varnish"
        self._current_value = 0
        self._current_str = ""
        self._current_type = ""

    def _start_element(self, name, attrs):
        self._current_element = name

    def _end_element(self, name):
        if name == "stat":
            m_name = self.normalize(self._current_metric)
            if self._current_type in ("a", "c"):
                self.rate(m_name, long(self._current_value), tags=self.tags)
            elif self._current_type in ("i", "g"):
                self.gauge(m_name, long(self._current_value), tags=self.tags)
                if 'n_purges' in m_name:
                    self.rate('varnish.n_purgesps', long(self._current_value), tags=self.tags)
            else:
                # Unsupported data type, ignore
                self._reset()
                return  # don't save

            # reset for next stat element
            self._reset()
        elif name in ("ident", "name") or (name == "type" and self._current_str != "MAIN"):
            self._current_metric += "." + self._current_str

    def _char_data(self, data):
        self.log.debug("Data %s [%s]", data, self._current_element)
        data = data.strip()
        if len(data) > 0 and self._current_element != "":
            if self._current_element == "value":
                self._current_value = long(data)
            elif self._current_element == "flag":
                self._current_type = data
            else:
                self._current_str = data

    def _get_varnish_stats(self, varnishstat_format):
        cmd = self.varnishstat_path + [self.VARNISHSTAT_FORMAT_OPTION[varnishstat_format]]
        for metric in self.metrics_filter:
            cmd.extend(["-f", metric])
        if self.name is not None:
            cmd.extend(['-n', self.name])

        output, _, _ = get_subprocess_output(cmd, self.log)
        return output

    def check(self, _):
        # Get version and version-specific args from varnishstat -V.
        version, varnishstat_format = self._get_version_info()
        varnish_stats_raw = self._get_varnish_stats(varnishstat_format)
        self._parse_varnishstat(varnish_stats_raw, varnishstat_format)

        # Parse service checks from varnishadm.
        if self.varnishadm:
            varnish_adm_raw = self._get_varnish_adm(version)
            if varnish_adm_raw:
                backends_by_status = self._parse_varnishadm(varnish_adm_raw)
                self._submit_backend_service_checks(backends_by_status)
        else:
            self.log.debug("Not collecting varnishadm because varnishadm is not set")

    def _get_varnish_adm(self, version):
        cmd = []
        if geteuid() != 0:
            cmd.append('sudo')

        if version < Version('4.1.0'):
            cmd.extend(self.varnishadm_path + ['-S', self.secretfile_path, 'debug.health'])
        else:
            cmd.extend(
                self.varnishadm_path
                + [
                    '-T',
                    '{}:{}'.format(self.daemon_host, self.daemon_port),
                    '-S',
                    self.secretfile_path,
                    'backend.list',
                    '-p',
                ]
            )

        err, output = None, None
        try:
            output, err, _ = get_subprocess_output(cmd, self.log, raise_on_empty_output=False)
        except OSError as e:
            self.log.error("There was an error running varnishadm. Make sure 'sudo' is available. %s", e)
            output = None
        if err or not output:
            self.log.error('Error getting service check from varnishadm: %s', err)
        return output

    def _get_version_info(self):
        # Get the varnish version from varnishstat
        output, error, _ = get_subprocess_output(self.varnishstat_path + ["-V"], self.log, raise_on_empty_output=False)

        # Assumptions regarding varnish's version
        varnishstat_format = "json"
        raw_version = None

        m1 = self.version_pattern.search(output, re.MULTILINE)
        # v2 prints the version on stderr, v3 on stdout
        m2 = self.version_pattern.search(error, re.MULTILINE)

        if m1 is None and m2 is None:
            self.log.warning("Cannot determine the version of varnishstat, assuming 3 or greater")
            self.warning("Cannot determine the version of varnishstat, assuming 3 or greater")
        else:
            if m1 is not None:
                raw_version = m1.group()
            elif m2 is not None:
                raw_version = m2.group()

        self.log.debug("Varnish version: %s", raw_version)

        if raw_version:
            self.set_metadata('version', raw_version)

        if raw_version is None:
            raw_version = '3.0.0'

        version = Version(raw_version)

        # Location of varnishstat
        if version < Version('3.0.0'):
            varnishstat_format = "text"
        elif version < Version('5.0.0'):  # we default to json starting version 5.0.0
            varnishstat_format = "xml"

        return version, varnishstat_format

    def _parse_varnishstat(self, output, varnishstat_format):
        """
        The text option (-1) is not reliable enough when counters get large.
        VBE.media_video_prd_services_01(10.93.67.16,,8080).happy18446744073709551615

        2 types of data, "a" for counter ("c" in newer versions of varnish), "i" for gauge ("g")
        https://github.com/varnish/Varnish-Cache/blob/master/include/tbl/vsc_fields.h

        Bitmaps are not supported.
        """
        # FIXME: this check is processing an unbounded amount of data
        # we should explicitly list the metrics we want to get from the check
        if varnishstat_format == "xml":
            p = xml.parsers.expat.ParserCreate()
            p.StartElementHandler = self._start_element
            p.EndElementHandler = lambda name: self._end_element(name)
            p.CharacterDataHandler = self._char_data
            self._reset()
            p.Parse(output, True)
        elif varnishstat_format == "json":
            json_output = json.loads(output)
            if "counters" in json_output:
                json_output = json_output["counters"]
            for name, metric in iteritems(json_output):
                if not isinstance(metric, dict):  # skip 'timestamp' field
                    continue

                if name.startswith("MAIN."):
                    name = name.split('.', 1)[1]

                metric_name = self.normalize(name, prefix="varnish")
                value = metric.get("value", 0)

                if metric.get("flag") in ("a", "c"):
                    self.rate(metric_name, long(value), tags=self.tags)
                elif metric.get("flag") in ("g", "i"):
                    self.gauge(metric_name, long(value), tags=self.tags)
                    if 'n_purges' in self.normalize(name, prefix="varnish"):
                        self.rate('varnish.n_purgesps', long(value), tags=self.tags)
                elif 'flag' not in metric:
                    self.log.warning("Could not determine the type of metric %s, skipping submission", metric_name)
                    self.log.debug("Raw metric %s is missing the `flag` field", str(metric))
        elif varnishstat_format == "text":
            for line in output.split("\n"):
                self.log.debug("Parsing varnish results: %s", line)
                fields = line.split()
                if len(fields) < 3:
                    break
                name, gauge_val, rate_val = fields[0], fields[1], fields[2]
                metric_name = self.normalize(name, prefix="varnish")

                # Now figure out which value to pick
                if rate_val.lower() in ("nan", "."):
                    # col 2 matters
                    self.log.debug("Varnish (gauge) %s %d", metric_name, int(gauge_val))
                    self.gauge(metric_name, int(gauge_val), tags=self.tags)
                    if 'n_purges' in metric_name:
                        self.rate('varnish.n_purgesps', float(gauge_val), tags=self.tags)
                else:
                    # col 3 has a rate (since restart)
                    self.log.debug("Varnish (rate) %s %d", metric_name, int(gauge_val))
                    self.rate(metric_name, float(gauge_val), tags=self.tags)

    def _parse_varnishadm(self, output):
        """Parse out service checks from varnishadm.

        Example output:

            Backend b0 is Sick
            Current states  good:  2 threshold:  3 window:  5
            Average responsetime of good probes: 0.000000
            Oldest                                                    Newest
            ================================================================
            -------------------------------------------------------------444 Good IPv4
            -------------------------------------------------------------XXX Good Xmit
            -------------------------------------------------------------RRR Good Recv
            ----------------------------------------------------------HHH--- Happy
            Backend b1 is Sick
            Current states  good:  2 threshold:  3 window:  5
            Average responsetime of good probes: 0.000000
            Oldest                                                    Newest
            ================================================================
            ----------------------------------------------------------HHH--- Happy

        Example output (new output format):

            Backend name                   Admin      Probe
            boot.default                   probe      Healthy (no probe)
            boot.backend2                  probe      Healthy 4/4
              Current states  good:  4 threshold:  3 window:  4
              Average response time of good probes: 0.002504
              Oldest ================================================== Newest
              --------------------------------------------------------------44 Good IPv4
              --------------------------------------------------------------XX Good Xmit
              --------------------------------------------------------------RR Good Recv
              ------------------------------------------------------------HHHH Happy

        Example output (v6):

            Backend name   Admin      Probe    Health     Last change
            boot.default   healthy    0/0      healthy    Mon, 16 Jan 2023 09:13:41 GMT
            boot.image     healthy    0/0      healthy    Mon, 16 Jan 2023 09:13:41 GMT

        """
        # Process status by backend.
        backends_by_status = defaultdict(list)
        for line in output.split("\n"):
            backend, status, message = None, None, None
            # split string and remove all empty fields
            tokens = filter(None, line.strip().split(' '))
            tokens = list(tokens)
            if len(tokens):
                if all(t in tokens for t in ['Backend', 'name', 'Admin', 'Probe']):
                    # skip the column headers that exist in new output format
                    continue
                # parse new output format
                # the backend name will include the vcl name
                # so split on first . to remove prefix
                elif len(tokens) >= 4 and tokens[1] in ['healthy', 'sick']:
                    # If the backend health was overridden, lets grab the
                    # overridden value instead of the probed health
                    backend = tokens[0].split('.', 1)[-1]
                    status = tokens[1].lower()
                elif len(tokens) >= 4 and tokens[1] == 'probe':
                    backend = tokens[0].split('.', 1)[-1]
                    status = tokens[2].lower()
                # Parse older Varnish backend output
                elif tokens[0] == 'Backend':
                    backend = tokens[1]
                    status = tokens[-1].lower()

                if tokens[0] == 'Current' and backend is not None:
                    try:
                        message = ' '.join(tokens[2:]).strip()
                    except Exception:
                        # If we can't parse a message still send a status.
                        self.log.exception('Error when parsing message from varnishadm')
                        message = ''

                if backend is not None:
                    backends_by_status[status].append((backend, message))
        return backends_by_status

    def _submit_backend_service_checks(self, backends_by_status):
        if backends_by_status is None:
            return

        for status, backends in iteritems(backends_by_status):
            check_status = BackendStatus.to_check_status(status)
            for backend, message in backends:
                service_checks_tags = ['backend:%s' % backend] + self.custom_tags
                self.service_check(self.SERVICE_CHECK_NAME, check_status, tags=service_checks_tags, message=message)
