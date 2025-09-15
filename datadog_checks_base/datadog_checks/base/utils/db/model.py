from datadog_checks.base.checks.base import AgentCheck


class DatabaseMonitoringAgentCheck(AgentCheck):
    def database_monitoring_query_sample(self, raw_event: str):
        self.event_platform_event(raw_event, "dbm-samples")

    def database_monitoring_query_metrics(self, raw_event: str):
        self.event_platform_event(raw_event, "dbm-metrics")

    def database_monitoring_query_activity(self, raw_event: str):
        self.event_platform_event(raw_event, "dbm-activity")

    def database_monitoring_metadata(self, raw_event: str):
        self.event_platform_event(raw_event, "dbm-metadata")
