# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2  # noqa: F401

from .metrics import METRIC_MAP, RENAME_LABELS_MAP
from .custom_scraper import CustomOpenMetricsScraper


class vLLMCheck(OpenMetricsBaseCheckV2):

    DEFAULT_METRIC_LIMIT = 0
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'vllm'

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
            "rename_labels": RENAME_LABELS_MAP,
        }

    @AgentCheck.metadata_entrypoint
    def _submit_version_metadata(self):

        endpoint = self.instance["openmetrics_endpoint"].replace("/metrics", "/version")
        response = self.http.get(endpoint)
        response.raise_for_status()

        data = response.json()
        version = data.get("version", "")
        version_split = version.split(".")
        if len(version_split) >= 3:
            major = version_split[0]
            minor = version_split[1]
            patch = version_split[2]

            version_raw = f'{major}.{minor}.{patch}'

            version_parts = {
                'major': major,
                'minor': minor,
                'patch': patch,
            }
            self.set_metadata('version', version_raw, scheme='semver', part_map=version_parts)
        else:
            self.log.debug("Invalid vLLM version format: %s", version)

    def check(self, instance):
        super().check(instance)
        self._submit_version_metadata()


    def configure_scrapers(self):
        """
        Configure custom scrapers.
        """
        self.scrapers = {}

        for config in self.scraper_configs:
            self.log.debug("Config loop is: %s", config)
            config["metrics"] = [METRIC_MAP]
            config["extra_metrics"] = ["ray_vllm:.+"]
            self.scrapers[config["openmetrics_endpoint"]] = CustomOpenMetricsScraper(
                self, config
            )

    def refresh_scrapers(self):
        """
        Refresh scrapers to include dynamically added metrics before scraping.
        """
        self.log.debug(
            "Starting refresh_scrapers. Current scrapers: %s",
            list(self.scrapers.keys()),
        )

        for endpoint, scraper in self.scrapers.items():
            self.log.debug("Processing scraper for endpoint: %s", endpoint)

            if isinstance(scraper, CustomOpenMetricsScraper):
                self.log.debug("Custom scraper detected for endpoint: %s", endpoint)

                dynamic_metrics = [
                    item.strip("'{} ")
                    for item in self.read_persistent_cache("modified_metrics").split(
                        ","
                    )
                ]

                self.log.debug(
                    "Dynamic metrics for endpoint %s: %s", endpoint, dynamic_metrics
                )

                current_metrics = scraper.config.get("metrics", [])
                self.log.debug(
                    "Current metrics for endpoint %s: %s", endpoint, current_metrics
                )

                existing_names = {
                    metric.get("name")
                    for metric in current_metrics
                    if isinstance(metric, dict) and "name" in metric
                }
                self.log.debug(
                    "Existing metric names for endpoint %s: %s",
                    endpoint,
                    existing_names,
                )

                for metric_name in dynamic_metrics:
                    if metric_name not in existing_names:
                        current_metrics[0][metric_name] = metric_name
                        self.log.debug(
                            "Added dynamic metric '%s' to config for endpoint %s",
                            metric_name,
                            endpoint,
                        )

                scraper.config["metrics"] = current_metrics
                self.log.debug(
                    "Updated metrics config for endpoint %s: %s",
                    endpoint,
                    scraper.config["metrics"],
                )

            else:
                self.log.debug("Skipping non-custom scraper for endpoint: %s", endpoint)
