try:
    from datadog_checks.base.utils.common import total_time_to_temporal_percent
except ImportError:

    # Provide fallback for agent < 6.16
    def total_time_to_temporal_percent(total_time, scale=1000):
        return total_time / scale * 100


try:
    from datadog_agent import get_config, read_persistent_cache, write_persistent_cache
except ImportError:

    def get_config(value):
        return ''

    def write_persistent_cache(value, key):
        pass

    def read_persistent_cache(value):
        return ''
