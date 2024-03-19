# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import copy
from datetime import datetime

import requests

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.time import get_timestamp

AIRFLOW_STATUS_OK = "OK"
AIRFLOW_STABLE_STATUS_OK = "healthy"


class AirflowCheck(AgentCheck):
    def __init__(self, name, init_config, instances):
        super(AirflowCheck, self).__init__(name, init_config, instances)

        self._url = self.instance.get('url', '')
        self._tags = self.instance.get('tags', [])

        # The Agent only makes one attempt to instantiate each AgentCheck so any errors occurring
        # in `__init__` are logged just once, making it difficult to spot. Therefore, we emit
        # potential configuration errors as part of the check run phase.
        # The configuration is only parsed once if it succeed, otherwise it's retried.
        self.check_initializations.append(self._parse_config)

    def check(self, _):
        tags = ['url:{}'.format(self._url)] + self._tags

        url_stable = self._url + "/api/v1/health"
        url_experimental = self._url + "/api/experimental/test"
        url_stable_version = self._url + "/api/v1/version"
        url_stable_task_instances = self._url + "/api/v1/dags/~/dagRuns/~/taskInstances?state=running"
        can_connect_status = AgentCheck.OK

        # Choose which version of Airflow to use
        if not self._get_version(url_stable_version):
            # Airflow version 1
            target_url = url_experimental
            submit_metrics = self._submit_healthy_metrics_experimental
        else:
            # Airflow version 2
            target_url = url_stable
            submit_metrics = self._submit_healthy_metrics_stable

        resp = self._get_json(target_url)
        if resp is None:
            can_connect_status = AgentCheck.CRITICAL
        else:
            submit_metrics(resp, tags)
            # Only calculate task duration for stable API
            if target_url is url_stable:
                task_instances = self._get_all_task_instances(url_stable_task_instances, tags)
                if task_instances:
                    self._calculate_task_ongoing_duration(task_instances, tags)
                else:
                    self.log.info("No running tasks found")

        self.service_check('airflow.can_connect', can_connect_status, tags=tags)
        self.gauge('airflow.can_connect', int(can_connect_status == AgentCheck.OK), tags=tags)

    def _get_version(self, url):
        """Get version from stable API `/api/v1/version`"""
        try:
            resp_payload = self.http.get(url)
            resp_payload.raise_for_status()
            resp_payload = resp_payload.json()
        except Exception as e:
            self.log.debug("Couldn't collect version from URL: %s with exception: %s", url, e)
        else:
            version = resp_payload.get('version')
            if version:
                self.log.debug("Airflow version: %s", version)
            return version

    def _submit_healthy_metrics_experimental(self, resp, tags):
        if resp.get('status') == AIRFLOW_STATUS_OK:
            health_status = AgentCheck.OK
        else:
            health_status = AgentCheck.CRITICAL

        self.service_check('airflow.healthy', health_status, tags=tags)
        self.gauge('airflow.healthy', int(health_status == AgentCheck.OK), tags=tags)

    def _submit_healthy_metrics_stable(self, resp, tags):
        metadb_status = resp.get('metadatabase', {}).get('status')
        scheduler_status = resp.get('scheduler', {}).get('status')

        if metadb_status == AIRFLOW_STABLE_STATUS_OK and scheduler_status == AIRFLOW_STABLE_STATUS_OK:
            health_status = AgentCheck.OK
            self.service_check('airflow.healthy', health_status, tags=tags)
        else:
            health_status = AgentCheck.CRITICAL
            message = "Metadatabase is {} and scheduler is {}".format(metadb_status, scheduler_status)
            self.service_check('airflow.healthy', health_status, tags=tags, message=message)

        self.gauge('airflow.healthy', int(health_status == AgentCheck.OK), tags=tags)

    def _get_all_task_instances(self, url, tags):
        resp = self._get_json(url)
        if not resp:
            return None

        total_tasks = resp.get('total_entries')
        self.log.info("Total running tasks: %s", total_tasks)
        self.gauge('airflow.dag.task.total_running', total_tasks, tags=tags)

        return resp.get('task_instances')

    def _calculate_task_ongoing_duration(self, tasks, tags):
        """
        Calculate the ongoing duration of each task in the given list of tasks.
        """

        for task in tasks:
            dag_task_tags = copy(tags)
            task_id = task.get('task_id')
            dag_id = task.get('dag_id')
            execution_date = task.get('execution_date')

            # Add tags for each task
            dag_task_tags.append('dag_id:{}'.format(dag_id))
            dag_task_tags.append('task_id:{}'.format(task_id))

            # Calculate ongoing duration
            ongoing_duration = get_timestamp() - datetime.fromisoformat((execution_date)).timestamp()
            self.gauge('airflow.dag.task.ongoing_duration', ongoing_duration, tags=dag_task_tags)

    def _parse_config(self):
        if not self._url:
            raise ConfigurationError('Missing configuration: url')

    def _get_json(self, url):
        try:
            resp = self.http.get(url)
            resp.raise_for_status()
            return resp.json()
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
            self.warning(
                "Couldn't connect to URL: %s with exception: %s. Please verify the address is reachable", url, e
            )
        except requests.exceptions.Timeout as e:
            self.warning("Connection timeout when connecting to %s: %s", url, e)
        return None
