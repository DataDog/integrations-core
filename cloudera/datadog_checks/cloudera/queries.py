
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
        'tags': [  # TODO: Add more tags
            ('cloudera_hostname', 'hostname'),
            ('entity_name', 'entityName'),
            ('host_id', 'hostId'),
            ('rack_id', 'rackId')
        ],
        'metric_name': 'cpu_system_rate'
    },
]

