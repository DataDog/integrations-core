from __future__ import annotations

from typing import TYPE_CHECKING

from datadog_checks.base.utils.common import pattern_filter

from .event import Event

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter


class Fallback:
    def __init__(
        self, key: str, value: str, custom_key: str, log: CheckLoggingAdapter, resolver: Fallback | None = None
    ):
        '''
        e.g Flow runs don't contain deployment_name, only id. So we use the deployment_id to lookup the deployment_name.
        - key is the name of the key used to lookup the value in the original obj. e.g deployment_id in deployments
          is "id"
        - value is the name of the key that contains the value in the original obj. e.g deployment_name in deployments
          is "name"
        - custom_key is the name of the key in the object that needs remapping. e.g deployment_id in flow runs

        e.g Task runs don't contain deployment_name, only information on the flow run. So we use the flow_run info to
        lookup the deployment_name.
        - key is the name of the key in the intermediate object. e.g flow_run_id in flow_runs is "id"
        - value is the name of the key that contains the value in the intermediate object. e.g deployment_id in flow
          runs is "deployment_id"
        - custom_key is the name of the key in the object that needs remapping. e.g flow_run_id in task runs
        - resolver is the fallback to resolve the value through. e.g self.deployment_fallback to parse deployment_id
          to deployment_name
        '''
        self.key = key  # which field to use as the mapping key e.g. "id"
        self.custom_key = custom_key  # which field to use for lookup e.g. "flow_run_id"
        self.value = value  # which field to use as the mapping value e.g. "name"
        self.resolver = resolver  # optional fallback to resolve the value through
        self.mappings: dict[str, str] = {}
        self.log = log

    def add_mapping(self, element: dict[str, str]):
        raw_value = element[self.value]
        if raw_value is None:
            self.log.debug("Value is None for key %s and value %s", self.key, self.value)
            return
        if self.resolver:
            raw_value = self.resolver.mappings.get(raw_value, raw_value)
        mapping_key = element[self.key]
        if mapping_key is None:
            self.log.debug("Mapping key is None for key %s and value %s", self.key, self.value)
            return
        self.mappings[mapping_key] = raw_value

    def get(self, element: dict[str, str]) -> str | None:
        return self.mappings.get(element.get(self.custom_key, ''))


class PrefectFilterMetrics:
    def __init__(
        self,
        log: CheckLoggingAdapter,
        work_pool_names: dict[str, list[str]] | None = None,
        work_queue_names: dict[str, list[str]] | None = None,
        deployment_names: dict[str, list[str]] | None = None,
        event_names: dict[str, list[str]] | None = None,
    ):
        self.log = log

        self.work_pool_names = work_pool_names or {}
        self.work_queue_names = work_queue_names or {}
        self.deployment_names = deployment_names or {}
        self.event_names = event_names or {}

        self.work_pool_cache: dict[str, bool] = {}
        self.work_queue_cache: dict[str, bool] = {}
        self.deployment_cache: dict[str, bool] = {}
        self.flow_run_cache: dict[str, bool] = {}
        self.task_run_cache: dict[str, bool] = {}
        self.event_cache: dict[str, bool] = {}

        self.deployment_fallback = Fallback("id", "name", "deployment_id", log)
        self.flow_run_fallback = Fallback("id", "flow_name", "flow_run_id", log)
        self.flow_run_to_work_pool_fallback = Fallback("id", "work_pool_name", "flow_run_id", log)
        self.flow_run_to_queue_fallback = Fallback("id", "work_queue_name", "flow_run_id", log)
        self.flow_run_to_deployment_fallback = Fallback(
            "id", "deployment_id", "flow_run_id", log, resolver=self.deployment_fallback
        )

    def filter_work_pools(self, work_pools: list[dict[str, str]]) -> list[dict[str, str]]:
        return self._filter_metric(
            self.work_pool_names,
            work_pools,
            {"name": (self.work_pool_cache, True, None)},
        )

    def filter_work_queues(self, work_queues: list[dict[str, str]]) -> list[dict[str, str]]:
        return self._filter_metric(
            self.work_queue_names,
            work_queues,
            {
                "work_pool_name": (self.work_pool_cache, False, None),
                "name": (self.work_queue_cache, True, None),
            },
        )

    def filter_deployments(self, deployments: list[dict[str, str]]) -> list[dict[str, str]]:
        return self._filter_metric(
            self.deployment_names,
            deployments,
            {
                "work_pool_name": (self.work_pool_cache, False, None),
                "work_queue_name": (self.work_queue_cache, False, None),
                "name": (self.deployment_cache, True, None),
            },
            [self.deployment_fallback],
        )

    def filter_flow_runs(self, flow_runs: list[dict[str, str]]) -> list[dict[str, str]]:
        return self._filter_metric(
            None,
            flow_runs,
            {
                "work_pool_name": (self.work_pool_cache, False, None),
                "work_queue_name": (self.work_queue_cache, False, None),
                "deployment_name": (self.deployment_cache, False, self.deployment_fallback),
            },
            [
                self.flow_run_to_deployment_fallback,
                self.flow_run_to_work_pool_fallback,
                self.flow_run_to_queue_fallback,
            ],
        )

    def filter_task_runs(self, task_runs: list[dict[str, str]]) -> list[dict[str, str]]:
        return self._filter_metric(
            None,
            task_runs,
            {
                "work_pool_name": (self.work_pool_cache, False, self.flow_run_to_work_pool_fallback),
                "work_queue_name": (self.work_queue_cache, False, self.flow_run_to_queue_fallback),
                "deployment_name": (self.deployment_cache, False, self.flow_run_to_deployment_fallback),
            },
        )

    def is_event_included(self, event: Event) -> bool:
        fields: dict[str, str] = {}
        caches: dict[str, tuple[dict[str, bool], bool, Fallback | None]] = {}
        fields["event_type"] = event.event_type
        caches["event_type"] = (self.event_cache, True, None)
        work_pool_name = event.event_related.get("work-pool", {}).get("name")
        if work_pool_name:
            fields["work_pool_name"] = work_pool_name
            caches["work_pool_name"] = (self.work_pool_cache, False, None)
        work_queue_name = event.event_related.get("work-queue", {}).get("name")
        if work_queue_name:
            fields["work_queue_name"] = work_queue_name
            caches["work_queue_name"] = (self.work_queue_cache, False, None)
        deployment_name = event.event_related.get("deployment", {}).get("name")
        if deployment_name:
            fields["deployment_name"] = deployment_name
            caches["deployment_name"] = (self.deployment_cache, False, None)

        return bool(
            self._filter_metric(
                self.event_names,
                [fields],
                caches,
            )
        )

    def _filter_metric(
        self,
        list_of_patterns: dict[str, list[str]] | None,
        list_to_filter_metric: list[dict[str, str]],
        caches: dict[str, tuple[dict[str, bool], bool, Fallback | None]],
        fallback_to_write: list[Fallback] | None = None,
    ) -> list[dict[str, str]]:
        result = []

        for e in list_to_filter_metric:
            for fallback in fallback_to_write or []:
                fallback.add_mapping(e)

            for field, (cache, check_pattern, fallback_to_use) in caches.items():
                value = None
                if field in e:
                    value = e.get(field)
                elif fallback_to_use:
                    value = fallback_to_use.get(e)
                else:
                    self.log.debug("Including event because no fallback or field found for %s", field)

                if value is not None and value not in cache and check_pattern:
                    if list_of_patterns:
                        cache[value] = bool(
                            pattern_filter(
                                [value],
                                whitelist=list_of_patterns.get("include", []),
                                blacklist=list_of_patterns.get("exclude", []),
                                key=lambda x: x,
                            )
                        )
                    else:
                        cache[value] = True

                if value is not None and value in cache and not cache[value]:
                    break
            else:
                result.append(e)
        return result
