# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.transform import get_native_dynamic_transformer
from datadog_checks.base.checks.openmetrics.v2.transformers.counter_gauge import get_counter_gauge
from datadog_checks.dcgm.metrics import IGNORED_TAGS, METRIC_MAP, RENAME_LABELS_MAP


class DcgmCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'dcgm'
    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self):
        return {
            "rename_labels": RENAME_LABELS_MAP,
            "ignored_tags": IGNORED_TAGS,
        }

    def configure_scrapers(self):
        super().configure_scrapers()
        self.scrapers[self.instance['openmetrics_endpoint']].metric_transformer.add_custom_transformer(
            "build_information",
            self._add_build_version_to_metadata,
        )
        self.scrapers[self.instance['openmetrics_endpoint']].metric_transformer.add_custom_transformer(
            r".*", self._add_gpu_tags, pattern=True
        )

    def _add_build_version_to_metadata(self, _metric, sample_data, _runtime_data):
        for sample, *_ in sample_data:
            self.set_metadata('version', sample.labels['build_version'].replace('_', '.'))

    def _add_gpu_tags(self, metric, sample_data, _runtime_data):
        metric_transformer = self.scrapers[self.instance['openmetrics_endpoint']].metric_transformer
        sample_list = list(sample_data)

        if not sample_list:
            return

        def add_tag_to_sample(entry):
            sample, tags, hostname = entry
            gpu_tags = []

            for tag in tags:
                if tag.startswith("UUID:"):
                    gpu_uuid = tag.replace("UUID:", "gpu_uuid:")
                    gpu_tags.append(gpu_uuid)
                elif tag.startswith("DCGM_FI_DEV_BRAND:"):
                    gpu_vendor = tag.replace("DCGM_FI_DEV_BRAND:", "gpu_vendor:")
                    gpu_tags.append(gpu_vendor)

            return sample, tags + gpu_tags, hostname

        metric_name = metric.name

        if metric_name not in METRIC_MAP:
            return

        new_metric_name = METRIC_MAP[metric_name]

        if isinstance(new_metric_name, dict):
            metric_type = new_metric_name.get("type")
            new_metric_name = new_metric_name["name"]
        else:
            metric_type = None

        modified_sample_data = (add_tag_to_sample(entry) for entry in sample_list)

        if metric_type == "counter_gauge":
            counter_gauge_transformer = get_counter_gauge(
                self, new_metric_name, None, metric_transformer.global_options
            )
            counter_gauge_transformer(metric, modified_sample_data, _runtime_data)
        else:
            native_transformer = get_native_dynamic_transformer(
                self, new_metric_name, None, metric_transformer.global_options
            )
            native_transformer(metric, modified_sample_data, _runtime_data)
