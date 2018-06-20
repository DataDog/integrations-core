# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import copy
import ldap3
import os
import ssl

from datadog_checks.checks import AgentCheck
from datadog_checks.errors import CheckException
from datadog_checks.config import is_affirmative


SEARCH_BASE = "cn=Monitor"
SEARCH_FILTER = "(objectClass=*)"
ATTRS = ["*", "+"]

METRIC_PREFIX = "openldap"

# Some docs here https://www.openldap.org/doc/admin24/monitoringslapd.html#Monitor%20Information
CONNECTIONS_METRICS_DN = "cn=connections,cn=monitor"
OPERATIONS_METRICS_DN = "cn=operations,cn=monitor"
STATISTICS_METRICS_DN = "cn=statistics,cn=monitor"
THREADS_METRICS_DN = "cn=threads,cn=monitor"
TIME_METRICS_DN = "cn=time,cn=monitor"
WAITERS_METRICS_DN = "cn=waiters,cn=monitor"


class OpenLDAP(AgentCheck):
    def check(self, instance):
        url, username, password, ssl_params, custom_queries, tags = self._get_instance_params(instance)

        server = ldap3.Server(url, tls=self._get_tls_object(ssl_params))
        conn = ldap3.Connection(server, username, password, collect_usage=True)

        # Try binding to the server
        try:
            res = conn.bind()
            if not res:
                raise ldap3.core.exceptions.LDAPBindError("Error binding to server: {}".format(conn.result))
        except ldap3.core.exceptions.LDAPBindError:
            self.log.exception("Could not connect to server at %s: %s", url, conn.result)
            self.service_check("{}.can_connect".format(METRIC_PREFIX), self.CRITICAL, tags=tags)
            raise

        self.service_check("{}.can_connect".format(METRIC_PREFIX), self.OK, tags=tags)
        bind_time = self._get_query_time(conn)
        self.gauge("{}.bind_time".format(METRIC_PREFIX), bind_time, tags=tags)

        try:
            # Search Monitor database to get all metrics
            conn.search(SEARCH_BASE, SEARCH_FILTER, attributes=ATTRS)
            self._collect_monitor_metrics(conn, tags)

            # Get additional custom metrics
            self._perform_custom_queries(conn, custom_queries, tags, instance)
        finally:
            conn.unbind()

    def _get_tls_object(self, ssl_params):
        """
        Return a TLS object to establish a secure connection to a server
        """
        if ssl_params is None:
            return None

        if not ssl_params["verify"] and ssl_params["ca_certs"]:
            self.warning("Incorrect configuration: trying to disable server certificate validation, "
                         "while also specifying a capath. No validation will be performed. Fix your "
                         "configuration to remove this warning")

        validate = ssl.CERT_REQUIRED if ssl_params["verify"] else ssl.CERT_NONE

        if ssl_params["ca_certs"] is None or os.path.isfile(ssl_params["ca_certs"]):
            tls = ldap3.core.tls.Tls(
                local_private_key_file=ssl_params["key"],
                local_certificate_file=ssl_params["cert"],
                ca_certs_file=ssl_params["ca_certs"],
                version=ssl.PROTOCOL_SSLv23,
                validate=validate,
            )
        elif os.path.isdir(ssl_params["ca_certs"]):
            tls = ldap3.core.tls.Tls(
                local_private_key_file=ssl_params["key"],
                local_certificate_file=ssl_params["cert"],
                ca_certs_path=ssl_params["ca_certs"],
                version=ssl.PROTOCOL_SSLv23,
                validate=validate,
            )
        else:
            raise CheckException("Invalid path {} for ssl_ca_certs: no such file or directory"
                                 .format(ssl_params["ca_certs"]))
        return tls

    def _get_instance_params(self, instance):
        """
        Parse instance configuration and perform minimal verification
        """
        url = instance.get("url")
        if url is None:
            raise CheckException("You must specify a url for your instance in `conf.yaml`")
        username = instance.get("username")
        password = instance.get("password")
        ssl_params = None
        if url.startswith("ldaps"):
            ssl_params = {
                "key": instance.get("ssl_key"),
                "cert": instance.get("ssl_cert"),
                "ca_certs": instance.get("ssl_ca_certs"),
                "verify": is_affirmative(instance.get("ssl_verify", True))
            }
        custom_queries = instance.get("custom_queries", [])
        tags = copy(instance.get("tags", []))
        tags.append("url:{}".format(url))

        return url, username, password, ssl_params, custom_queries, tags

    def _collect_monitor_metrics(self, conn, tags):
        """
        Collect metrics from the monitor backend
        """
        for entry in conn.entries:
            # Get metrics from monitor backend
            dn = entry.entry_dn.lower()
            if dn.endswith(CONNECTIONS_METRICS_DN):
                self._handle_connections_entry(entry, tags)
            elif dn.endswith(OPERATIONS_METRICS_DN):
                self._handle_operations_entry(entry, tags)
            elif dn.endswith(STATISTICS_METRICS_DN):
                self._handle_statistics_entry(entry, tags)
            elif dn.endswith(THREADS_METRICS_DN):
                self._handle_threads_entry(entry, tags)
            elif dn.endswith(TIME_METRICS_DN):
                self._handle_time_entry(entry, tags)
            elif dn.endswith(WAITERS_METRICS_DN):
                self._handle_waiters_entry(entry, tags)

    def _perform_custom_queries(self, conn, custom_queries, tags, instance):
        """
        Perform custom queries to collect additional metrics like number of result and duration of the query
        """
        for query in custom_queries:
            name = query.get("name")
            if name is None:
                self.log.error("`name` field is required for custom query")
                continue
            search_base = query.get("search_base")
            if search_base is None:
                self.log.error("`search_base` field is required for custom query #%s", name)
                continue
            search_filter = query.get("search_filter")
            if search_filter is None:
                self.log.error("`search_filter` field is required for custom query #%s", name)
                continue
            attrs = query.get("attributes")
            if "username" in query:
                username = query.get("username")
                password = query.get("password")
                if not username:
                    # username is an empty string, we want anonymous bind
                    username = None
                    password = None
            else:
                # username not specified, we want to reuse the credentials for the monitor backend
                username = instance.get("username")
                password = instance.get("password")

            try:
                # Rebind with different credentials
                auth_method = ldap3.SIMPLE if username else ldap3.ANONYMOUS
                if username is None:
                    conn.user = None
                res = conn.rebind(user=username, password=password, authentication=auth_method)
                if not res:
                    raise ldap3.core.exceptions.LDAPBindError("Error binding to server: {}".format(conn.result))
            except ldap3.core.exceptions.LDAPBindError:
                self.log.exception("Could not rebind to server at %s to perform query %s", instance.get("url"), name)
                continue

            try:
                # Perform the search query
                res = conn.search(search_base, search_filter, attributes=attrs)
            except ldap3.core.exceptions.LDAPException:
                self.log.exception("Unable to perform search query for %s", name)
                continue

            query_time = self._get_query_time(conn)
            results = len(conn.entries)
            self.gauge("{}.query.duration".format(METRIC_PREFIX), query_time, tags=tags + ["query:{}".format(name)])
            self.gauge("{}.query.entries".format(METRIC_PREFIX), results, tags=tags + ["query:{}".format(name)])

    def _handle_connections_entry(self, entry, tags):
        cn = self._extract_common_name(entry.entry_dn)
        if cn in ["max_file_descriptors", "current"]:
            self.gauge("{}.connections.{}".format(METRIC_PREFIX, cn), entry["monitorCounter"].value, tags=tags)
        elif cn == "total":
            self.monotonic_count("{}.connections.{}".format(METRIC_PREFIX, cn),
                                 entry["monitorCounter"].value, tags=tags)

    def _handle_operations_entry(self, entry, tags):
        cn = self._extract_common_name(entry.entry_dn)
        initiated = entry["monitorOpInitiated"].value
        completed = entry["monitorOpCompleted"].value
        if cn == "operations":
            # the root of the "cn=operations,cn=monitor" has the total number of initiated and completed operations
            self.monotonic_count("{}.operations.initiated.total".format(METRIC_PREFIX), initiated, tags=tags)
            self.monotonic_count("{}.operations.completed.total".format(METRIC_PREFIX), completed, tags=tags)
        else:
            self.monotonic_count("{}.operations.initiated".format(METRIC_PREFIX),
                                 initiated, tags=tags + ["operation:{}".format(cn)])
            self.monotonic_count("{}.operations.completed".format(METRIC_PREFIX),
                                 completed, tags=tags + ["operation:{}".format(cn)])

    def _handle_statistics_entry(self, entry, tags):
        cn = self._extract_common_name(entry.entry_dn)
        if cn != "statistics":
            self.monotonic_count("{}.statistics.{}".format(METRIC_PREFIX, cn), entry["monitorCounter"].value, tags=tags)

    def _handle_threads_entry(self, entry, tags):
        cn = self._extract_common_name(entry.entry_dn)
        try:
            value = entry["monitoredInfo"].value
        except ldap3.core.exceptions.LDAPKeyError:
            pass
        if cn in ["max", "max_pending"]:
            self.gauge("{}.threads.{}".format(METRIC_PREFIX, cn), value, tags=tags)
        elif cn in ["open", "starting", "active", "pending", "backload"]:
            self.gauge("{}.threads".format(METRIC_PREFIX), value, tags=tags + ["status:{}".format(cn)])

    def _handle_time_entry(self, entry, tags):
        cn = self._extract_common_name(entry.entry_dn)
        if cn == "uptime":
            self.gauge("{}.uptime".format(METRIC_PREFIX), entry["monitoredInfo"].value, tags=tags)

    def _handle_waiters_entry(self, entry, tags):
        cn = self._extract_common_name(entry.entry_dn)
        if cn != "waiters":
            self.gauge("{}.waiter.{}".format(METRIC_PREFIX, cn), entry["monitorCounter"].value, tags=tags)

    def _extract_common_name(self, dn):
        """
        extract first common name (cn) from DN that looks like "cn=max file descriptors,cn=connections,cn=monitor"
        """
        dn = dn.lower().replace(" ", "_")
        return dn.split(",")[0].split("=")[1]

    def _get_query_time(self, conn):
        return (conn.usage.last_received_time - conn.usage.last_transmitted_time).total_seconds()
