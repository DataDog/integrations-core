# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.common import total_time_to_temporal_percent
from datadog_checks.base.utils.constants import MICROSECOND


class Statistics:
    NAME: str
    GAUGES = set()
    COUNTS = set()
    TEMPORAL_PERCENTS = {}

    def full_metric_name(self, metric):
        return f'{self.NAME}.{metric}'

    def submit(self, check, data, tags):
        for metric, value in data.items():
            if metric in self.GAUGES:
                check.gauge(self.full_metric_name(metric), value, tags=tags)
            elif metric in self.COUNTS:
                check.count(self.full_metric_name(metric), value, tags=tags)
            elif metric in self.TEMPORAL_PERCENTS:
                metric_data = self.TEMPORAL_PERCENTS[metric]
                check.rate(
                    self.full_metric_name(metric_data.get('name', metric)),
                    total_time_to_temporal_percent(value, scale=metric_data['scale']),
                    tags=tags,
                )


class MessageFlowStatistics(Statistics):
    NAME = 'MessageFlow'
    GAUGES = [
        'MaximumCPUTime',
        'MaximumElapsedTime',
        'MaximumSizeOfInputMessages',
        'MinimumCPUTime',
        'MinimumElapsedTime',
        'MinimumSizeOfInputMessages',
        'NumberOfThreadsInPool',
    ]
    COUNTS = [
        'TimesMaximumNumberOfThreadsReached',
        'TotalInputMessages',
        'TotalNumberOfBackouts',
        'TotalNumberOfCommits',
        'TotalNumberOfErrorsProcessingMessages',
        'TotalNumberOfMQErrors',
        'TotalNumberOfMessagesWithErrors',
        'TotalNumberOfTimeOutsWaitingForRepliesToAggregateMessages',
        'TotalSizeOfInputMessages',
    ]
    TEMPORAL_PERCENTS = {
        'CPUTimeWaitingForInputMessage': {'scale': MICROSECOND},
        'ElapsedTimeWaitingForInputMessage': {'scale': MICROSECOND},
        'TotalCPUTime': {'scale': MICROSECOND, 'name': 'CPUTime'},
        'TotalElapsedTime': {'scale': MICROSECOND, 'name': 'ElapsedTime'},
    }

    def submit(self, check, data, tags):
        tags = [
            f'integration_node:{data["BrokerLabel"]}',
            f'integration_server:{data["ExecutionGroupName"]}',
            f'message_flow:{data["MessageFlowName"]}',
            f'application:{data["ApplicationName"]}',
            f'accounting_origin:{data["AccountingOrigin"]}',
            *tags,
        ]
        super().submit(check, data, tags)


STATISTICS = {'MessageFlow': MessageFlowStatistics}


def get_statistics(name):
    if name not in STATISTICS:
        return

    return STATISTICS[name]()
