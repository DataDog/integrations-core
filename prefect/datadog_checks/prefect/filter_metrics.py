from __future__ import annotations

from datadog_checks.base.utils.common import pattern_filter

from .event_manager import EventManager


class Fallback:
    def __init__(self, key: str, value: str, custom_key: str, resolver: Fallback | None = None):
        self.key = key  # which field to use as the mapping key e.g. "id"
        self.custom_key = custom_key  # which field to use for lookup e.g. "flow_run_id"
        self.value = value  # which field to use as the mapping value e.g. "name"
        self.resolver = resolver  # optional fallback to resolve the value through
        self.mappings: dict[str, str] = {}

    def add_mapping(self, element: dict[str, str]):
        raw_value = element[self.value]
        if self.resolver:
            raw_value = self.resolver.mappings.get(raw_value, raw_value)
        self.mappings[element[self.key]] = raw_value

    def get(self, element: dict[str, str]) -> str | None:
        return self.mappings.get(element.get(self.custom_key, ''))


class PrefectFilterMetrics:
    def __init__(
        self,
        work_pool_names: dict[str, list[str]] | None = None,
        work_queue_names: dict[str, list[str]] | None = None,
        deployment_names: dict[str, list[str]] | None = None,
        event_names: dict[str, list[str]] | None = None,
    ):
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

        self.deployment_fallback = Fallback("id", "name", "deployment_id")
        self.flow_run_fallback = Fallback("id", "flow_name", "flow_run_id")
        self.flow_run_to_work_pool_fallback = Fallback("id", "work_pool_name", "flow_run_id")
        self.flow_run_to_queue_fallback = Fallback("id", "work_queue_name", "flow_run_id")
        self.flow_run_to_deployment_fallback = Fallback(
            "id", "deployment_id", "flow_run_id", resolver=self.deployment_fallback
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

    def is_event_included(self, event: EventManager) -> bool:
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
                if field in e:
                    value = e.get(field)
                elif fallback_to_use:
                    value = fallback_to_use.get(e)

                if not value:
                    break

                if value not in cache and check_pattern:
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

                if not cache[value]:
                    break
            else:
                result.append(e)
        return result
