import re
from copy import deepcopy

from prometheus_client.metrics_core import Metric
from prometheus_client.samples import Sample

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper
from datadog_checks.ray.config_models import ConfigMixin




class CustomOpenMetricsScraper(OpenMetricsScraper):
    def __init__(self, check, config):
        super(CustomOpenMetricsScraper, self).__init__(check, config)
        self.modified_metric_names = set()

    def scrape(self):
        """
        Overrides the scrape method to add custom logic for filtering and processing metrics.
        """

        runtime_data = {
            "flush_first_value": self.flush_first_value,
            "static_tags": self.static_tags,
        }

        metrics = self.consume_metrics(runtime_data)

        for metric in metrics:

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
                self.write_persistent_cache(
                    "modified_metrics", str(self.modified_metric_names)
                )

            transformer = self.get(metric)
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

            if raw_metric_name != escaped_metric_name:
                config.pop("name", None)
                self.metric_transformer.metric_patterns.append(
                    (re.compile(raw_metric_name), config)
                )
            else:
                try:
                    transformer = self.metric_transformer.compile_transformer(config)
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