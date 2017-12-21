# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

'''
Check the performance counters from IIS
'''

# project
from checks import AgentCheck
try:
    from checks.libs.win.pdhbasecheck import PDHBaseCheck
except ImportError:
    def PDHBaseCheck(*args, **kwargs):
        return

from utils.containers import hash_mutable

DEFAULT_COUNTERS = [
    ["Web Service", None, "Service Uptime", "iis.uptime", "gauge"],
    # Network
    ["Web Service", None, "Bytes Sent/sec", "iis.net.bytes_sent", "gauge"],
    ["Web Service", None, "Bytes Received/sec", "iis.net.bytes_rcvd", "gauge"],
    ["Web Service", None, "Bytes Total/sec", "iis.net.bytes_total", "gauge"],
    ["Web Service", None, "Current Connections", "iis.net.num_connections", "gauge"],
    ["Web Service", None, "Files Sent/sec", "iis.net.files_sent", "gauge"],
    ["Web Service", None, "Files Received/sec", "iis.net.files_rcvd" ,"gauge"],
    ["Web Service", None, "Total Connection Attempts (all instances)", "iis.net.connection_attempts", "gauge"],

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
class IIS(PDHBaseCheck):
    SERVICE_CHECK = "iis.site_up"


    def __init__(self, name, init_config, agentConfig, instances):
        PDHBaseCheck.__init__(self, name, init_config, agentConfig, instances=instances, counter_list=DEFAULT_COUNTERS)

    def check(self, instance):

        sites = instance.get('sites')
        if sites is None:
            expected_sites = set()
        else:
            expected_sites = set(sites)
        # _Total should always be in the list of expected sites; we always
        # report _Total
        if "_Total" not in expected_sites:
            expected_sites.add("_Total")

        self.log.debug("expected sites is %s" % str(expected_sites))
        key = hash_mutable(instance)
        for inst_name, dd_name, metric_func, counter in self._metrics[key]:
            try:
                try:
                    vals = counter.get_all_values()
                except Exception as e:
                    self.log.error("Failed to get_all_values %s %s" % (inst_name, dd_name))
                    continue

                for sitename, val in vals.iteritems():
                    tags = []
                    if key in self._tags:
                        tags = self._tags[key]

                    try:
                        if not counter.is_single_instance():
                            # Skip any sites we don't specifically want.
                            if not sites:
                                tags.append("site:{0}".format(self.normalize(sitename)))
                            # always report total
                            elif sitename == "_Total":
                                tags.append("site:{0}".format(self.normalize(sitename)))
                            elif sitename not in sites:
                                continue
                            else:
                                tags.append("site:{0}".format(self.normalize(sitename)))
                    except Exception as e:
                        self.log.error("Caught exception %s setting tags" % str(e))

                    try:
                        metric_func(dd_name, val, tags)
                    except Exception as e:
                        self.log.error("metric_func: %s %s %s" % (dd_name, str(val), str(e)))
                        pass

                    if dd_name == "iis.uptime":
                        uptime = int(val)
                        status = AgentCheck.CRITICAL if uptime == 0 else AgentCheck.OK
                        self.service_check(self.SERVICE_CHECK, status, tags=['site:{0}'.format(self.normalize(sitename))])
                        if sitename in expected_sites:
                            self.log.debug("Removing %s from expected sites" % sitename)
                            expected_sites.remove(sitename)
                        else:
                            self.log.warning("site not in expected_sites %s" % sitename)

            except Exception as e:
                # don't give up on all of the metrics because one failed
                self.log.error("IIS Failed to get metric data for %s %s: %s" % (inst_name, dd_name, str(e)))
                pass

        for site in expected_sites:
            self.service_check(self.SERVICE_CHECK, AgentCheck.CRITICAL,
                            tags=['site:{0}'.format(self.normalize(site))])
