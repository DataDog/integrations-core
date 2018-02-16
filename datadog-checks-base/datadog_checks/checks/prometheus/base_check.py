# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .mixins import PrometheusScraper

from .. import AgentCheck
from ...errors import CheckException

class Scraper(PrometheusScraper):
    def __init__(self, check):
        super(Scraper, self).__init__()
        self.check = check

    def _submit_gauge(self, metric_name, val, metric, custom_tags=None, hostname=None):
        """
        Submit a metric as a gauge, additional tags provided will be added to
        the ones from the label provided via the metrics object.

        `custom_tags` is an array of 'tag:value' that will be added to the
        metric when sending the gauge to Datadog.
        """
        _tags = []
        if custom_tags is not None:
            _tags += custom_tags
        for label in metric.label:
            if self.exclude_labels is None or label.name not in self.exclude_labels:
                tag_name = label.name
                if self.labels_mapper is not None and label.name in self.labels_mapper:
                    tag_name = self.labels_mapper[label.name]
                _tags.append('{}:{}'.format(tag_name, label.value))
        _tags = self._finalize_tags_to_submit(_tags, metric_name, val, metric, custom_tags=custom_tags, hostname=hostname)
        self.check.gauge('{}.{}'.format(self.NAMESPACE, metric_name), val, _tags, hostname=hostname)

    def _submit_service_check(self, *args, **kwargs):
        self.check.service_check(*args, **kwargs)


class GenericPrometheusCheck(AgentCheck):
    """
    GenericPrometheusCheck is a class that helps instanciating PrometheusCheck only
    with YAML configurations. As each check has it own states it maintains a map
    of all checks so that the one corresponding to the instance is executed

    Minimal example configuration:
    instances:
    - prometheus_url: http://foobar/endpoint
        namespace: "foobar"
        metrics:
        - bar
        - foo
    """
    def __init__(self, name, init_config, agentConfig, instances=None):
        super(GenericPrometheusCheck, self).__init__(name, init_config, agentConfig, instances)
        self.scrapers_map = {}
        for instance in instances:
            self.get_scraper(instance)

    def check(self, instance):
        endpoint = instance["prometheus_url"]
        scraper = self.get_scraper(instance)
        if not scraper.metrics_mapper:
            raise CheckException("You have to collect at least one metric from the endpoint: " + endpoint)

        scraper.process(
            endpoint,
            send_histograms_buckets=instance.get('send_histograms_buckets', True),
            instance=instance,
            ignore_unmapped=True
        )

    def get_scraper(self, instance):
        endpoint = instance.get("prometheus_url", "")
        # If we already created the corresponding Scraper, return it
        if endpoint in self.scrapers_map:
            return self.scrapers_map[endpoint]

        # Otherwise we create the PrometheusCheck
        if endpoint == "":
            raise CheckException("Unable to find prometheus URL in config file.")
        namespace = instance.get("namespace", "")
        if namespace == "":
            raise CheckException("You have to define a namespace for each prometheus check")
        # Instanciate check
        scraper = Scraper(self)
        scraper.NAMESPACE = namespace
        # Metrics are preprocessed if no mapping
        metrics_mapper = {}
        for metric in instance.get("metrics", []):
            if isinstance(metric, basestring):
                metrics_mapper[metric] = metric
            else:
                metrics_mapper.update(metric)
        scraper.metrics_mapper = metrics_mapper
        scraper.labels_mapper = instance.get("labels_mapper", {})
        scraper.label_joins = instance.get("label_joins", {})
        scraper.exclude_labels = instance.get("exclude_labels", [])
        scraper.label_to_hostname = instance.get("label_to_hostname", None)
        scraper.health_service_check = instance.get("health_service_check", True)
        scraper.ssl_cert = instance.get("ssl_cert", None)
        scraper.ssl_private_key = instance.get("ssl_private_key", None)
        scraper.ssl_ca_cert = instance.get("ssl_ca_cert", None)

        self.scrapers_map[instance["prometheus_url"]] = scraper

        return scraper
