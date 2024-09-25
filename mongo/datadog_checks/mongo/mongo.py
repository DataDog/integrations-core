# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from copy import deepcopy

from datadog_checks.base import AgentCheck
from datadog_checks.mongo.api import CRITICAL_FAILURE
from datadog_checks.mongo.common import (
    SERVICE_CHECK_NAME,
)
from datadog_checks.mongo.config import MongoConfig
from datadog_checks.mongo.dbm.operation_samples import MongoOperationSamples
from datadog_checks.mongo.dbm.schemas import MongoSchemas
from datadog_checks.mongo.dbm.slow_operations import MongoSlowOperations
from datadog_checks.mongo.mongo_instance import MongoInstance

from . import metrics

long = int


class MongoDb(AgentCheck):
    """
    MongoDB agent check.

    # Metrics
    Metric available for collection are listed by topic as `MongoDb` class variables.

    Various metric topics are collected by default. Others require the
    corresponding option enabled in the check configuration file.

    ## Format
    Metrics are listed with the following format:
        ```
        metric_name -> metric_type
        ```
        or
        ```
        metric_name -> (metric_type, alias)*
        ```

    * `alias` parameter is optional, if unspecified, MongoDB metrics are reported
       with their original metric names.

    # Service checks
    * `mongodb.can_connect`
      Connectivity health to the instance.
    """

    def __init__(self, name, init_config, instances=None):
        super(MongoDb, self).__init__(name, init_config, instances)
        self._config = MongoConfig(self.instance, self.log)

        if 'server' in self.instance:
            self.warning('Option `server` is deprecated and will be removed in a future release. Use `hosts` instead.')

        # Get the list of metrics to collect
        self.metrics_to_collect = self._build_metric_list_to_collect()
        self.last_states_by_server = {}

        self.diagnosis.register(self._diagnose_tls)

        self.mongo_instances = []

        # DBM
        self._operation_samples = MongoOperationSamples(check=self)
        self._slow_operations = MongoSlowOperations(check=self)
        self._schemas = MongoSchemas(check=self)

    def _build_metric_list_to_collect(self):
        """
        Build the metric list to collect based on the instance preferences.
        """
        metrics_to_collect = {}

        # Default metrics
        for default_metrics in metrics.DEFAULT_METRICS.values():
            metrics_to_collect.update(default_metrics)

        # Additional metrics metrics
        for option in self._config.additional_metrics:
            if option not in metrics.AVAILABLE_METRICS:
                if option in metrics.DEFAULT_METRICS:
                    self.log.warning(
                        u"`%s` option is deprecated. The corresponding metrics are collected by default.", option
                    )
                else:
                    self.log.warning(
                        u"Failed to extend the list of metrics to collect: unrecognized `%s` option", option
                    )
                continue
            additional_metrics = metrics.AVAILABLE_METRICS[option]
            self.log.debug(u"Adding `%s` corresponding metrics to the list of metrics to collect.", option)
            metrics_to_collect.update(additional_metrics)

        return metrics_to_collect

    def _refresh_mongo_instances(self):
        """
        Refresh the list of MongoDB instances to collect.
        """
        if not self.mongo_instances:
            connection_host = self._config.server or self._config.hosts
            self.mongo_instances = [
                MongoInstance(
                    self,
                    connection_host=connection_host,
                    connection_options=self._config,
                    reported_database_hostname=self._config.reported_database_hostname,
                )
            ]

    def check(self, _):
        try:
            self._refresh_mongo_instances()
            for mongo_instance in self.mongo_instances:
                mongo_instance.refresh()

            # DBM
            if self._config.dbm_enabled:
                tags = deepcopy(self._config.metric_tags)
                self._operation_samples.run_job_loop(tags=tags)
                self._slow_operations.run_job_loop(tags=tags)
                self._schemas.run_job_loop(tags=tags)
        except CRITICAL_FAILURE as e:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self._config.service_check_tags)
            raise e  # Let exception bubble up to global handler and show full error in the logs.
        else:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=self._config.service_check_tags)

    def _diagnose_tls(self):
        # Check TLS config. Specifically, we might want to check that if `tls` is
        # enabled (either explicitly or implicitly), the provided
        # tls_certificate_key_file and tls_ca_file actually exist on the file system.
        if "tls_certificate_key_file" in self.instance:
            self._diagnose_readable('tls', self.instance["tls_certificate_key_file"], "tls_certificate_key_file")
        if "tls_ca_file" in self.instance:
            self._diagnose_readable('tls', self.instance["tls_ca_file"], "tls_ca_file")

    def _diagnose_readable(self, name, path, option_name):
        try:
            open(path).close()
        except FileNotFoundError:
            self.diagnosis.fail(name, f"file `{path}` provided in the `{option_name}` option does not exist")
        except OSError as exc:
            self.diagnosis.fail(
                name,
                f"file `{path}` provided as the `{option_name}` option could not be opened: {exc.strerror}",
            )
        else:
            self.diagnosis.success(
                name,
                f"file `{path}` provided as the `{option_name}` exists and is readable",
            )

    def cancel(self):
        if self._config.dbm_enabled:
            self._operation_samples.cancel()
            self._slow_operations.cancel()
