
# Each query is of format:
# query - the actual query
# tags - a list of tuples containing (datadog_tag_name, cloudera_attribute_name)
# metric_name - the name of the Datadog metric name
# TODO: Add other timeseries metrics
TIMESERIES_QUERIES = [
    {
        'query_string': 'select last(cpu_soft_irq_rate)',
        'tags': [
            ('cloudera_hostname', 'hostname'),
            ('cluster_display_name', 'clusterDisplayName'),
            ('entity_name', 'entityName'),
            ('cluster_name', 'clusterName'),
            ('host_id', 'hostId'),
            ('rack_id', 'rackId')
        ],
        'metric_name': 'cpu_soft_irq_rate'
    },
    {
        'query_string': 'select last(cpu_system_rate)',
        'tags': [
            ('cloudera_hostname', 'hostname'),
            ('entity_name', 'entityName'),
            ('host_id', 'hostId'),
            ('rack_id', 'rackId'),
            ('cluster_display_name', 'clusterDisplayName'),
        ],
        'metric_name': 'cpu_system_rate'
    },
    {
        'query_string': 'select last(load_1)',
        'tags': [
            ('cloudera_hostname', 'hostname'),
            ('entity_name', 'entityName'),
            ('host_id', 'hostId'),
            ('rack_id', 'rackId'),
            ('cluster_display_name', 'clusterDisplayName'),
        ],
        'metric_name': 'load_1'
    },
    {
        'query_string': 'select last(physical_memory_cached)',
        'tags': [
            ('cloudera_hostname', 'hostname'),
            ('entity_name', 'entityName'),
            ('host_id', 'hostId'),
            ('rack_id', 'rackId'),
            ('cluster_display_name', 'clusterDisplayName'),
        ],
        'metric_name': 'physical_memory_cached'
    },
    {
        'query_string': 'select last(mem_rss)',
        'tags': [
            ('cloudera_hostname', 'hostname'),
            ('entity_name', 'entityName'),
            ('host_id', 'hostId'),
            ('rack_id', 'rackId'),
            ('cluster_display_name', 'clusterDisplayName'),
            ('role_type', 'roleType'),
            ('service_display_name', 'serviceDisplayName'),
        ],
        'metric_name': 'mem_rss'
    },
    {
        'query_string': 'select last(swap_out_rate)',
        'tags': [
            ('cloudera_hostname', 'hostname'),
            ('entity_name', 'entityName'),
            ('host_id', 'hostId'),
            ('rack_id', 'rackId'),
            ('cluster_display_name', 'clusterDisplayName'),
            ('role_type', 'roleType'),
            ('service_display_name', 'serviceDisplayName'),
        ],
        'metric_name': 'swap_out_rate'
    },
    {
        'query_string': 'select last(total_bytes_receive_rate_across_network_interfaces)',
        'tags': [
            ('cloudera_hostname', 'hostname'),
            ('entity_name', 'entityName'),
            ('host_id', 'hostId'),
            ('rack_id', 'rackId'),
            ('cluster_display_name', 'clusterDisplayName'),
            ('role_type', 'roleType'),
            ('service_display_name', 'serviceDisplayName'),
            ('role_config_group', 'roleConfigGroup'),
        ],
        'metric_name': 'total_bytes_receive_rate_across_network_interfaces'
    },
    {
        'query_string': 'select last(await_time)',
        'tags': [
            ('cloudera_hostname', 'hostname'),
            ('entity_name', 'entityName'),
            ('host_id', 'hostId'),
            ('rack_id', 'rackId'),
            ('cluster_display_name', 'clusterDisplayName'),
            ('role_type', 'roleType'),
            ('service_display_name', 'serviceDisplayName'),
        ],
        'metric_name': 'await_time'
    }


]

