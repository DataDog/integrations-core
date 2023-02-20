# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Mapping of the Statistic type to which attribute contains the metric value
# noqa E501 IBM Docs https://www.ibm.com/docs/en/was-nd/9.0.5?topic=pmi-data-classification
METRIC_VALUE_FIELDS = {
    'AverageStatistic': 'count',
    'BoundedRangeStatistic': 'value',
    'CountStatistic': 'count',
    'DoubleStatistic': 'double',
    'RangeStatistic': 'value',
    'TimeStatistic': 'totalTime',
}

# Mapping the Name of the Stat object to the metric prefix
# noqa E501 IBM Docs - https://www.ibm.com/docs/en/was-nd/9.0.5?topic=pmi-data-organization
METRIC_CATEGORIES = {
    'JVM Runtime': 'jvm',
    'JDBC Connection Pools': 'jdbc',
    'Servlet Session Manager': 'servlet_session',
    'Thread Pools': 'thread_pools',
}

CATEGORY_FIELDS = {'Stat'}

# Each Stat Node will have a predictable set up sub Nodes that containing
# more Stat Nodes and eventually metrics. This maps each Stat Node to what the tag key needs
# to be for that Stat. For Ex, the JDBC stat will have one sub Stat node representing a Provider
# which has a sub node representing a DataSource, so we need to know what to tag by.
NESTED_TAGS = {
    'jdbc': ['provider', 'dataSource'],
    'servlet_session': ['web_application'],
    'thread_pools': ['thread_pool'],
}
