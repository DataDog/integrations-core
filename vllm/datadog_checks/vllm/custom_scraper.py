import re
from copy import deepcopy

from prometheus_client.metrics_core import Metric
from prometheus_client.samples import Sample

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper
from datadog_checks.vllm.config_models import ConfigMixin


class CustomOpenMetricsScraper(OpenMetricsScraper):
    def __init__(self, check, config):
        super(CustomOpenMetricsScraper, self).__init__(check, config)
        self.modified_metric_names = set()

    def scrape(self):
        """
        Overrides the scrape method to add custom logic for filtering and processing metrics. Recreates metric samples to be submitted with new metric name.
        """
        self.log.debug("Starting custom scrape for endpoint: %s", self.endpoint)
        self.log.debug("Scraping with current list: %s", self.config.get("metrics"))

        runtime_data = {
            "flush_first_value": self.flush_first_value,
            "static_tags": self.static_tags,
        }

        metrics = self.consume_metrics(runtime_data)

        for metric in metrics:
            self.log.debug("Processing metric custom: %s", metric.name)

            if metric.name.startswith("ray_vllm:"):
                self.log.debug("Custom processing for ray_vllm metric: %s", metric.name)
                new_name = metric.name.replace("ray_vllm:", "")

                updated_samples = [
                    Sample(
                        name=new_name,
                        labels=sample.labels,
                        value=sample.value,
                        timestamp=sample.timestamp,
                        exemplar=sample.exemplar,
                    )
                    for sample in metric.samples
                ]

                metric = Metric(
                    name=new_name,
                    documentation=metric.documentation,
                    typ=metric.type,
                    unit=metric.unit,
                )
                metric.samples = updated_samples
                self.modified_metric_names.add(new_name)
                self.log.debug("Modified metric: %s", metric)
                self.log.debug(
                    "Modified metric name list is: %s of type %s",
                    self.modified_metric_names,
                    type(self.modified_metric_names),
                )
                self.write_persistent_cache(
                    "modified_metrics", str(self.modified_metric_names)
                )

            transformer = self.get(metric)
            self.log.debug("Transformer obj is %s", transformer)
            if transformer is not None:
                transformer(metric, self.generate_sample_data(metric), runtime_data)

        self.flush_first_value = True

        metrics_config = deepcopy(
            self.metric_transformer.normalize_metric_config(self.config)
        )

        self.metric_transformer.transformer_data = {}
        self.metric_transformer.metric_patterns = []
        for raw_metric_name, config in metrics_config.items():
            escaped_metric_name = re.escape(raw_metric_name)
            self.log.debug(
                "Raw metric name is: %s, config is %s", raw_metric_name, config
            )

            if raw_metric_name != escaped_metric_name:
                config.pop("name", None)
                self.metric_transformer.metric_patterns.append(
                    (re.compile(raw_metric_name), config)
                )
            else:
                try:
                    self.log.debug(
                        "Compiling transformer for metric: %s", raw_metric_name
                    )
                    self.log.debug("Transformer config: %s", config)
                    transformer = self.metric_transformer.compile_transformer(config)
                    self.log.debug("Compiled transformer: %s", transformer)
                    self.metric_transformer.transformer_data[
                        raw_metric_name
                    ] = transformer

                except Exception as e:
                    error_message = (
                        f"Error compiling transformer for metric `{raw_metric_name}`: {e}\n"
                        f"Metric config: {config}\n"
                        f"Transformer data before error: {self.metric_transformer.transformer_data}"
                    )
                    self.log.error(error_message)
                    raise type(e)(error_message) from None

    def get(self, metric):
        """
        Retrieve or dynamically create a transformer for the given metric.
        """
        metric_name = metric.name
        DEFAULT_METRIC_TYPE = "native"

        transformer_data = self.metric_transformer.transformer_data.get(metric_name)
        self.log.debug(
            " self Transformer data is: %s", self.metric_transformer.transformer_data
        )
        if transformer_data is not None:
            metric_type, transformer = transformer_data
            if (
                metric_type == DEFAULT_METRIC_TYPE
                and self.metric_transformer.skip_native_metric(metric)
            ):
                return

            return transformer
        elif self.metric_transformer.metric_patterns:
            for metric_pattern, config in self.metric_transformer.metric_patterns:
                if metric_pattern.search(metric_name):
                    (
                        metric_type,
                        transformer,
                    ) = self.metric_transformer.compile_transformer(
                        {"name": metric_name, **config}
                    )
                    if self.metric_transformer.cache_metric_wildcards:
                        self.metric_transformer.transformer_data[metric_name] = (
                            metric_type,
                            transformer,
                        )

                    if (
                        metric_type == DEFAULT_METRIC_TYPE
                        and self.metric_transformer.skip_native_metric(metric)
                    ):
                        return

                    return transformer

        self.log.debug(
            "Skipping metric `%s` as it is not defined in `metrics`", metric_name
        )
