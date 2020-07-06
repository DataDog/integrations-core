try:
    import datadog_agent

    from ..log import CheckLoggingAdapter, init_logging

    init_logging()
except ImportError:
    pass
