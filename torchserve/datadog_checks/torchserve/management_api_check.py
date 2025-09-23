# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import json
import time
from urllib.parse import urljoin

from datadog_checks.base import AgentCheck
from datadog_checks.torchserve.model_discovery import ModelDiscovery

WORKER_STATUSES = {
    "UNKNOWN": 0,
    "READY": 1,
    "LOADING": 2,
    "UNLOADING": 3,
}


class TorchserveManagementAPICheck(AgentCheck):
    __NAMESPACE__ = 'torchserve.management_api'
    SERVICE_CHECK_NAME = 'health'
    CHECK_NAME = "torchserve"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_discovery = None
        self.submit_events = None
        self.tags = None
        self.__previous_models = None
        self.check_initializations.append(self.parse_config)

    def parse_config(self):
        self.model_discovery = ModelDiscovery(
            self,
            limit=self.instance.get("limit", 100),
            include=self.instance.get("include", [".*"]),
            exclude=self.instance.get("exclude", []),
            interval=self.instance.get("interval"),
        )
        self.submit_events = self.instance.get("submit_events", True)
        self.tags = self.instance.get("tags", [])
        self.tags.append(f"management_api_url:{self.instance['management_api_url']}")

    def check(self, _):
        for _, _, model, _ in self.model_discovery.get_items():
            self.process_one_model(model)

        self.service_check(self.SERVICE_CHECK_NAME, self.model_discovery.api_status, tags=self.tags)

        if self.model_discovery.api_status == AgentCheck.OK and self.submit_events and self.model_discovery.refreshed:
            if self.previous_models is not None:
                self.compare_models_and_emit_events(self.previous_models, self.model_discovery.all_models)

            self.previous_models = self.model_discovery.all_models

    def process_one_model(self, model):
        self.log.debug("Processing model [%s]", model['modelName'])
        model_name = model['modelName']
        endpoint = f"models/{model_name}/all"
        url = urljoin(self.instance["management_api_url"], endpoint)

        try:
            response = self.http.get(url)
            response.raise_for_status()
            content = response.json()
        except Exception as e:
            self.log.error("Caught exception %s querying model %s.", e, model_name)
            return

        self.gauge("model.versions", len(content), tags=self.tags + [f"model_name:{model_name}"])

        for model_details in content:
            self.process_one_version(model, model_details)

    def process_one_version(self, model, model_details):
        self.log.debug(
            "Processing version [%s] for model [%s]", model_details['modelVersion'], model_details['modelName']
        )

        tags = copy.deepcopy(self.tags)
        tags += [f"model_name:{model_details['modelName']}", f"model_version:{model_details['modelVersion']}"]

        self.gauge("model.workers.current", len(model_details.get("workers", [])), tags=tags)
        self.gauge("model.workers.min", model_details.get("minWorkers"), tags=tags)
        self.gauge("model.workers.max", model_details.get("maxWorkers"), tags=tags)
        self.gauge("model.batch_size", model_details.get("batchSize"), tags=tags)
        self.gauge("model.max_batch_delay", model_details.get("maxBatchDelay"), tags=tags)
        self.gauge("model.is_loaded_at_startup", 1 if model_details.get("loadedAtStartup", False) else 0, tags=tags)
        self.gauge(
            "model.version.is_default", 1 if model_details.get("modelUrl") == model.get("modelUrl") else 0, tags=tags
        )

        for worker in model_details.get("workers", []):
            self.process_one_worker(worker, model_details, tags)

    def process_one_worker(self, worker, model_details, model_tags):
        self.log.debug(
            "Processing worker [%s] for version [%s] of model [%s]",
            worker["id"],
            model_details['modelVersion'],
            model_details['modelName'],
        )

        tags = model_tags + [
            f"worker_id:{worker.get('id')}",
            f"worker_pid:{worker.get('pid')}",
        ]

        self.gauge("model.worker.memory_usage", worker.get("memoryUsage"), tags=tags)
        self.gauge("model.worker.is_gpu", 1 if worker.get("gpu", False) else 0, tags=tags)
        self.gauge("model.worker.status", WORKER_STATUSES.get(worker.get("status"), 0), tags=tags)

    @property
    def previous_models(self):
        if self.__previous_models:
            return self.__previous_models

        if previous_models := self.read_persistent_cache("previous_models"):
            self.__previous_models = json.loads(previous_models)
            return self.__previous_models

        return None

    @previous_models.setter
    def previous_models(self, value):
        self.__previous_models = value
        self.write_persistent_cache("previous_models", json.dumps(value))

    def compare_models_and_emit_events(self, previous_models, current_models):
        for previous_key, previous_value in previous_models.items():
            current_value = current_models.get(previous_key)

            if not current_value:
                self.log.debug("Model [%s] has been removed", previous_key)
                self.event(
                    self.__create_event(
                        f"{self.__NAMESPACE__}.model_removed",
                        "A model has been removed",
                        f"The model [{previous_key}] has been removed.",
                        self.tags + [f"model_name:{previous_key}"],
                    ),
                )
                continue

            if current_value != previous_value:
                self.log.debug(
                    "New default value for model [%s] set from [%s] to [%s]",
                    previous_key,
                    previous_value,
                    current_value,
                )
                self.event(
                    self.__create_event(
                        f"{self.__NAMESPACE__}.default_version_changed",
                        "A new default version has been set for a model",
                        f"A new default version has been set for the model [{previous_key}], "
                        f"from file [{previous_value}] to file [{current_value}].",
                        self.tags + [f"model_name:{previous_key}"],
                    )
                )

        for model_name, model_url in [(k, v) for (k, v) in current_models.items() if k not in previous_models]:
            self.log.debug("Model [%s] has been added", model_name)
            self.event(
                self.__create_event(
                    f"{self.__NAMESPACE__}.model_added",
                    "A new model has been added",
                    f"The model [{model_name}] has been added with the file [{model_url}].",
                    self.tags + [f"model_name:{model_name}"],
                ),
            )

    def __create_event(self, type, title, message, tags):
        return {
            'timestamp': time.time(),
            'event_type': type,
            'msg_title': title,
            'msg_text': message,
            'alert_type': 'info',
            'source_type_name': self.CHECK_NAME,
            'host': self.hostname,
            'tags': tags,
        }
