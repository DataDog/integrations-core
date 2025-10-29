from .metrics_generated import METRIC_DATA

# Mis-named or legacy metric names in Couchbase.
RAW_METRIC_NAME_MAP = {
    "audit_queue_length": "cm_audit_queue_length",
    "audit_unsuccessful_retries": "cm_audit_unsuccessful_retries",
    "couch_docs_actual_disk_size": "kv_couch_docs_actual_disk_size",
    "couch_spatial_data_size": "kv_couch_spatial_data_size",
    "couch_spatial_disk_size": "kv_couch_spatial_disk_size",
    "couch_spatial_ops": "kv_couch_spatial_ops",
    "couch_views_actual_disk_size": "kv_couch_views_actual_disk_size",
    "couch_views_data_size": "kv_couch_views_data_size",
    "couch_views_disk_size": "kv_couch_views_disk_size",
    "couch_views_ops": "kv_couch_views_ops",
    "total_knn_queries_rejected_by_throttler": "fts_num_knn_queries_rejected_by_throttler",
}


def metric_data_couchbase_to_datadog(metric_data):
    """Transform metric data from Couchbase to Datadog.

    Example: kv_dcp_backoff becomes kv.dcp_backoff.

    This also renames some mis-named or legacy metric names.

    This is useful when fetching the metric definitions from Couchbase, to
    compare them to the metrics we have in metadata.csv (which have Datadog
    names). See compare_upstream_metrics.py for an example.
    """

    datadog_metric_data = []
    for md in metric_data:
        metric_name = md["metric_name"]

        # Fix mis-named or legacy metric names.
        metric_name = RAW_METRIC_NAME_MAP.get(metric_name, metric_name)

        # Split the service name from the rest of the metric name.
        service_name, partial_metric_name = metric_name.split("_", 1)

        # Make the Datadog metric name, e.g. `kv.dcp_backoff`. The check
        # namespace "couchbase." will be prepended automatically.
        metric_name = ".".join(
            (
                service_name,
                partial_metric_name,
            )
        )

        md_datadog = md.copy()
        md_datadog["metric_name"] = metric_name

        datadog_metric_data.append(md_datadog)

    return datadog_metric_data


def metric_data_datadog_to_couchbase(metric_data):
    """Transform metric data from Datadog to Couchbase.

    Example: kv.dcp_backoff becomes kv_dcp_backoff.

    This also renames some mis-named or legacy metric names.

    This is used to generate the metric map and type overrides.
    """

    couchbase_metric_data = []
    for md in metric_data:
        metric_name = md["metric_name"]

        # Split the metric name on first dot, e.g. `kv.dcp_backoff` or `sync_gateway.cache.hits`.
        service_name, partial_metric_name = metric_name.split(".", 1)

        # Make the Couchbase metric name, e.g. `kv_dcp_backoff`.
        metric_name = "_".join((service_name, partial_metric_name))

        # Re-apply mis-named or legacy metric names.
        inverse_metric_name_map = {v: k for k, v in RAW_METRIC_NAME_MAP.items()}
        metric_name = inverse_metric_name_map.get(metric_name, metric_name)

        md_couchbase = md.copy()
        md_couchbase["metric_name"] = metric_name

        couchbase_metric_data.append(md_couchbase)

    return couchbase_metric_data


def get_metric_map_couchbase_to_datadog():
    """Use metric data from metadata.csv to produce the metric name map."""

    datadog_metric_data = METRIC_DATA
    couchbase_metric_data = metric_data_datadog_to_couchbase(datadog_metric_data)

    # This works because the metric_data arrays are sorted, and stay sorted.
    metric_map = {}
    for index, metric in enumerate(couchbase_metric_data):
        metric_map[metric["metric_name"]] = datadog_metric_data[index]["metric_name"]

        if metric["metric_type"] == "histogram":
            # Couchbase's /metrics endpoint rarely or never return proper type
            # indicators for histograms. This causes problems in the Datadog
            # scraper internals: The metric parser sees the xxx_bucket metric,
            # and assigns the "unknown" type to it, and the metric is silently
            # discarded.
            #
            # Therefore we add type overrides for the xxx_bucket metrics so they
            # get the "histogram" type; see the special handling of this in
            # get_type_overrides below.
            #
            # Histograms come with three suffixes: _bucket, _count, and _sum.
            # We need to map all three to the base metric name so they can be
            # processed together as a histogram.
            for suffix in ["_bucket", "_count", "_sum"]:
                metric_name_with_suffix = metric["metric_name"] + suffix
                metric_map[metric_name_with_suffix] = datadog_metric_data[index]["metric_name"]

    return metric_map


def get_type_overrides():
    """Use metric data from metadata.csv to produce the type overrides."""

    datadog_metric_data = METRIC_DATA

    # Get the Couchbase raw metric names, because type overrides apply before
    # metric names are mapped.
    couchbase_metric_data = metric_data_datadog_to_couchbase(datadog_metric_data)

    type_overrides = {}
    for metric_data in couchbase_metric_data:
        type_overrides[metric_data["metric_name"]] = metric_data["metric_type"]

        if metric_data["metric_type"] == "histogram":
            # Add type overrides for xxx_bucket, xxx_count, and xxx_sum metric names,
            # to make the Datadog scraper handle them as histograms. Otherwise they would
            # remain with type "unknown" and get silently dropped. See details
            # in get_metric_map_couchbase_to_datadog above.
            for suffix in ["_bucket", "_count", "_sum"]:
                metric_name_with_suffix = metric_data["metric_name"] + suffix
                type_overrides[metric_name_with_suffix] = metric_data["metric_type"]

    return type_overrides


def construct_metrics_config():
    """Construct metrics config for OpenMetricsBaseCheckV2.

    Converts the metric map and type overrides into V2's array format.
    """
    metric_map = get_metric_map_couchbase_to_datadog()
    type_overrides = get_type_overrides()

    metrics = []
    for raw_metric_name, datadog_metric_name in metric_map.items():
        config = {raw_metric_name: {'name': datadog_metric_name}}

        if raw_metric_name in type_overrides:
            config[raw_metric_name]['type'] = type_overrides[raw_metric_name]

        metrics.append(config)

    return metrics
