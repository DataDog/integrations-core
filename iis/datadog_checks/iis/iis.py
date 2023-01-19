# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from six import PY3, iteritems

from datadog_checks.base import PDHBaseCheck, is_affirmative

from .service_check import app_pool_service_check, site_service_check

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
    # Application Pools
    ["APP_POOL_WAS", None, "Current Application Pool State", "iis.app_pool.state", "gauge"],
    ["APP_POOL_WAS", None, "Current Application Pool Uptime", "iis.app_pool.uptime", "gauge"],
    ["APP_POOL_WAS", None, "Total Application Pool Recycles", "iis.app_pool.recycle.count", "monotonic_count"],
]

TOTAL_INSTANCE = '_Total'


class IIS(PDHBaseCheck):
    SITE = 'site'
    APP_POOL = 'app_pool'

    def __new__(cls, name, init_config, instances):
        if PY3 and not is_affirmative(instances[0].get('use_legacy_check_version', False)):
            from .check import IISCheckV2

            return IISCheckV2(name, init_config, instances)
        else:
            return super(IIS, cls).__new__(cls)

    def __init__(self, name, init_config, instances):
        super(IIS, self).__init__(name, init_config, instances, counter_list=DEFAULT_COUNTERS)
        self._sites = self.instance.get('sites', [])
        self._app_pools = self.instance.get('app_pools', [])

        self._expected_data = ((self.SITE, self._sites), (self.APP_POOL, self._app_pools))
        self._remaining_data = {namespace: set() for namespace, _ in self._expected_data}

    def check(self, _):
        self.do_refresh_counters()
        self.reset_remaining_data()

        for inst_name, dd_name, metric_func, counter in self._metrics[self.instance_hash]:
            try:
                counter_values = self.get_counter_values(counter)
            except Exception as e:
                self.log.error("Failed to get_all_values %s %s: %s", inst_name, dd_name, e)
                continue

            try:
                if counter.english_class_name == 'Web Service':
                    self.collect_sites(dd_name, metric_func, counter, counter_values)
                elif counter.english_class_name == 'APP_POOL_WAS':
                    self.collect_app_pools(dd_name, metric_func, counter, counter_values)
                else:
                    self.log.debug(
                        "Unknown IIS counter: %s. Falling back to default submission.", counter.english_class_name
                    )
                    for instance_name, val in iteritems(counter_values):
                        tags = list(self._tags.get(self.instance_hash, []))

                        if not counter.is_single_instance():
                            tag = "instance:{}".format(instance_name)
                            tags.append(tag)
                        metric_func(dd_name, val, tags)

            except Exception as e:
                # don't give up on all of the metrics because one failed
                self.log.error("IIS Failed to get metric data for %s %s: %s", inst_name, dd_name, e)

        self._report_unavailable_values()

    def collect_sites(self, dd_name, metric_func, counter, counter_values):
        namespace = self.SITE
        remaining_sites = self._remaining_data[namespace]

        for site_name, value in iteritems(counter_values):
            is_single_instance = counter.is_single_instance()
            if (
                not is_single_instance
                and site_name != TOTAL_INSTANCE
                and site_name not in self._sites
                # Collect all if not selected
                and self._sites
            ):
                self.log.debug(
                    "Skipping site metric %s: single instance: %s, site name: %s, counter: %s",
                    dd_name,
                    str(is_single_instance),
                    site_name,
                    str(counter),
                )
                continue

            tags = self._get_tags(namespace, site_name, is_single_instance)
            try:
                metric_func(dd_name, value, tags)
            except Exception as e:
                self.log.error('Error in metric_func: %s %s %s', dd_name, value, e)

            if dd_name == 'iis.uptime':
                status = site_service_check(value)
                self._report_service_check(namespace, status, tags)
                if site_name in remaining_sites:
                    self.log.debug('Removing %r from expected sites', site_name)
                    remaining_sites.remove(site_name)
                else:
                    self.log.warning('Site %r not in expected sites', site_name)

    def collect_app_pools(self, dd_name, metric_func, counter, counter_values):
        namespace = self.APP_POOL
        remaining_app_pools = self._remaining_data[namespace]

        for app_pool_name, value in iteritems(counter_values):
            is_single_instance = counter.is_single_instance()
            if (
                not is_single_instance
                and app_pool_name != TOTAL_INSTANCE
                and app_pool_name not in self._app_pools
                # Collect all if not selected
                and self._app_pools
            ):
                self.log.debug(
                    "Skipping app pool metric %s: single instance: %s, site name: %s, counter: %s",
                    dd_name,
                    str(is_single_instance),
                    app_pool_name,
                    str(counter),
                )
                continue

            tags = self._get_tags(namespace, app_pool_name, is_single_instance)
            try:
                metric_func(dd_name, value, tags)
            except Exception as e:
                self.log.error('Error in metric_func: %s %s %s', dd_name, value, e)

            if dd_name == 'iis.app_pool.state':
                status = app_pool_service_check(value)
                self._report_service_check(namespace, status, tags)
                if app_pool_name in remaining_app_pools:
                    self.log.debug('Removing %r from expected app pools', app_pool_name)
                    remaining_app_pools.remove(app_pool_name)
                else:
                    self.log.warning('App pool %r not in expected app pools', app_pool_name)

    def _report_service_check(self, namespace, status, tags):
        self.service_check(self.get_service_check_up(namespace), status, tags)

    def _report_unavailable_values(self):
        for namespace, remaining_values in self._remaining_data.items():
            service_check_uptime = self.get_service_check_up(namespace)

            for value in remaining_values:
                tags = self._get_tags(namespace, value, False)
                self.log.warning('Did not get any data for expected %s: %s', namespace, value)
                self.service_check(service_check_uptime, self.CRITICAL, tags)

    def _get_tags(self, name, value, is_single_instance):
        tags = []
        if self.instance_hash in self._tags:
            tags = list(self._tags[self.instance_hash])
        tags.append(self.get_iishost())

        if not is_single_instance:
            try:
                tags.append('{}:{}'.format(name, self.normalize_tag(value)))
            except Exception as e:
                self.log.error('Error setting %s tags: %s', name, e)

        return tags

    def get_iishost(self):
        inst_host = self.instance.get('host')
        if inst_host in ['.', 'localhost', '127.0.0.1', None]:
            # Use agent's hostname if connecting to local machine.
            iis_host = self.hostname
        else:
            iis_host = inst_host
        return 'iis_host:{}'.format(self.normalize_tag(iis_host))

    @classmethod
    def get_service_check_up(cls, namespace):
        return 'iis.{}_up'.format(namespace)

    def reset_remaining_data(self):
        for namespace, expected_values in self._expected_data:
            remaining_values = self._remaining_data[namespace]
            remaining_values.clear()
            remaining_values.update(expected_values)

            # Ensure that we always report _Total
            remaining_values.add(TOTAL_INSTANCE)

            self.log.debug('Expecting %ss: %s', namespace, remaining_values)
