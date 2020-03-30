# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from six import iteritems

from datadog_checks.base import PDHBaseCheck
try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

DEFAULT_COUNTERS = [
    ["Web Service", None, "Service Uptime", "iis.uptime", "gauge"],
    # Network
    ["Web Service", None, "Bytes Sent/sec", "iis.net.bytes_sent", "gauge"],
    ["Web Service", None, "Bytes Received/sec", "iis.net.bytes_rcvd", "gauge"],
    ["Web Service", None, "Bytes Total/sec", "iis.net.bytes_total", "gauge"],
    ["Web Service", None, "Current Connections", "iis.net.num_connections", "gauge"],
    ["Web Service", None, "Files Sent/sec", "iis.net.files_sent", "gauge"],
    ["Web Service", None, "Files Received/sec", "iis.net.files_rcvd", "gauge"],
    ["Web Service", None, "Total Connection Attempts (all instances)", "iis.net.connection_attempts", "gauge"],
    ["Web Service", None, "Connection Attempts/sec", "iis.net.connection_attempts_sec", "gauge"],
    # HTTP Methods
    ["Web Service", None, "Get Requests/sec", "iis.httpd_request_method.get", "gauge"],
    ["Web Service", None, "Post Requests/sec", "iis.httpd_request_method.post", "gauge"],
    ["Web Service", None, "Head Requests/sec", "iis.httpd_request_method.head", "gauge"],
    ["Web Service", None, "Put Requests/sec", "iis.httpd_request_method.put", "gauge"],
    ["Web Service", None, "Delete Requests/sec", "iis.httpd_request_method.delete", "gauge"],
    ["Web Service", None, "Options Requests/sec", "iis.httpd_request_method.options", "gauge"],
    ["Web Service", None, "Trace Requests/sec", "iis.httpd_request_method.trace", "gauge"],
    # Errors
    ["Web Service", None, "Not Found Errors/sec", "iis.errors.not_found", "gauge"],
    ["Web Service", None, "Locked Errors/sec", "iis.errors.locked", "gauge"],
    # Users
    ["Web Service", None, "Anonymous Users/sec", "iis.users.anon", "gauge"],
    ["Web Service", None, "NonAnonymous Users/sec", "iis.users.nonanon", "gauge"],
    # Requests
    ["Web Service", None, "CGI Requests/sec", "iis.requests.cgi", "gauge"],
    ["Web Service", None, "ISAPI Extension Requests/sec", "iis.requests.isapi", "gauge"],
]

TOTAL_SITE = "_Total"


class IIS(PDHBaseCheck):
    SERVICE_CHECK = "iis.site_up"

    def __init__(self, name, init_config, instances):
        super(IIS, self).__init__(name, init_config, instances=instances, counter_list=DEFAULT_COUNTERS)
        self.sites = self.instance.get('sites') or []

    def get_iishost(self):
        inst_host = self.instance.get("host")
        if inst_host in [".", "localhost", "127.0.0.1", None]:
            # Use agent's hostname if connecting to local machine.
            iis_host = datadog_agent.get_hostname()
        else:
            iis_host = inst_host
        return "iis_host:{}".format(self.normalize_tag(iis_host))

    def check(self, _):
        if self.refresh_counters:
            for counter, values in list(iteritems(self._missing_counters)):
                self._make_counters(self.instance_hash, ([counter], values))

        expected_sites = set(self.sites)
        # _Total should always be in the list of expected sites; we always
        # report _Total
        expected_sites.add(TOTAL_SITE)
        self.log.debug("Expected sites is %s", expected_sites)

        for inst_name, dd_name, metric_func, counter in self._metrics[self.instance_hash]:
            try:
                site_values = counter.get_all_values()
            except Exception as e:
                self.log.error("Failed to get_all_values %s %s: %s", inst_name, dd_name, e)
                continue
            try:
                for site_name, value in iteritems(site_values):
                    is_single_instance = counter.is_single_instance()
                    if (
                        not is_single_instance
                        and self.sites
                        and site_name != TOTAL_SITE
                        and site_name not in self.sites
                    ):
                        continue

                    tags = self._get_site_tags(site_name, is_single_instance)
                    try:
                        metric_func(dd_name, value, tags)
                    except Exception as e:
                        self.log.error("Error in metric_func: %s %s %s", dd_name, value, e)

                    if dd_name == "iis.uptime":
                        self._report_uptime(value, tags)
                        if site_name in expected_sites:
                            self.log.debug("Removing %r from expected sites", site_name)
                            expected_sites.remove(site_name)
                        else:
                            self.log.warning("Site %r not in expected_sites", site_name)

            except Exception as e:
                # don't give up on all of the metrics because one failed
                self.log.error("IIS Failed to get metric data for %s %s: %s", inst_name, dd_name, e)

        self._report_unavailable_sites(expected_sites)

    def _report_uptime(self, site_uptime, tags):
        uptime = int(site_uptime)
        status = self.CRITICAL if uptime == 0 else self.OK
        self.service_check(self.SERVICE_CHECK, status, tags)

    def _report_unavailable_sites(self, remaining_sites):
        for site in remaining_sites:
            tags = []
            if self.instance_hash in self._tags:
                tags = list(self._tags[self.instance_hash])
            tags.append(self.get_iishost())
            normalized_site = self.normalize_tag(site)
            tags.append("site:{}".format(normalized_site))
            self.log.warning("Check didn't get any data for expected site: %r", site)
            self.service_check(self.SERVICE_CHECK, self.CRITICAL, tags)

    def _get_site_tags(self, site_name, is_single_instance):
        tags = []
        if self.instance_hash in self._tags:
            tags = list(self._tags[self.instance_hash])
        tags.append(self.get_iishost())

        try:
            if not is_single_instance:
                tags.append("site:{}".format(self.normalize_tag(site_name)))
        except Exception as e:
            self.log.error("Caught exception %r setting tags", e)

        return tags
