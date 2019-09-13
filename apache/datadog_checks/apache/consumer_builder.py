# @TODO see if we cannot move this functions at common level


def _build_metric_consumer_fct(transform_value=None, **kwargs):
    """
    Optimized for cases where we convert to one or 2 calls
    This function will build a shortcut function to publish a metric

    Example: function to manage 'Total kBytes' from apache

    fct = _build_metric_consumer_fct(transform_value=lambda x: float(x) * 1024,
                                     gauge='apache.net.bytes',
                                     rate='apache.net.bytes_per_s')

    fct(self, '10')

    will do:

    value = float('10') * 1024
    self.gauge('apache.net.bytes', value)
    self.rate('apache.net.bytes_per_s', value)
    """
    if transform_value is None:
        if len(kwargs) == 1:
            fct_name, name = kwargs.popitem()

            def fct(self, value, tags=None, hostname=None, device_name=None):
                getattr(self, fct_name)(name, value, tags, hostname, device_name)

        elif len(kwargs) == 2:
            f1, n1 = kwargs.popitem()
            f2, n2 = kwargs.popitem()

            def fct(self, value, tags=None, hostname=None, device_name=None):
                getattr(self, f1)(n1, value, tags, hostname, device_name)
                getattr(self, f2)(n2, value, tags, hostname, device_name)
        else:
            def fct(self, value, tags, hostname=None, device_name=None):
                for fct_n, m_name in kwargs.items():
                    getattr(self, fct_n)(m_name, value, tags, hostname, device_name)
    else:
        if len(kwargs) == 1:
            fct_name, name = kwargs.popitem()

            def fct(self, value, tags=None, hostname=None, device_name=None):
                getattr(self, fct_name)(name, transform_value(value), tags, hostname, device_name)

        elif len(kwargs) == 2:
            f1, n1 = kwargs.popitem()
            f2, n2 = kwargs.popitem()

            def fct(self, value, tags=None, hostname=None, device_name=None):
                value = transform_value(value)
                getattr(self, f1)(n1, value, tags, hostname, device_name)
                getattr(self, f2)(n2, value, tags, hostname, device_name)
        else:
            def fct(self, value, tags=None, hostname=None, device_name=None):
                value = transform_value(value)
                for fct_n, m_name in kwargs.items():
                    getattr(self, fct_n)(m_name, value, tags, hostname, device_name)

    return fct


def build_metric_consumer_fct_map(metric_mappings, default_transform_value=None):
    """
    This methods will provide a map of function for your class,
    to redirect depending on a key, to one or multiple method call(s).

    Example:

    class MyAgent(AgentCheck):

        METRIC_FCT_MAP = build_metric_consumer_fct_map({
            'Total kBytes': {'gauge': 'apache.net.bytes',
                             'rate': 'apache.net.bytes_per_s',
                             'transform_value': lambda value: float(value) * 1024},
            'ConnsTotal': {'gauge': 'apache.conns_total'},
        }, default_transform_value=float)

        def consume_lines(lines):
            for line in lines:
                metric, value = line.split(': ')
                fct = self.METRIC_FCT_MAP.get(metric, None)
                if fct is not None:
                    fct(self, value, tags)

    a = MyAgent()

    a.consume_lines(['Total kBytes: 10', 'ConnsTotal: 42'])

    Will do the same as:

    a.gauge('apache.net.bytes', 10240)
    a.rate('apache.net.bytes_per_s', 10240)
    a.gauge('apache.conns_total', 42)
    """

    metric_fct_map = {}
    for name, args in metric_mappings.items():
        if 'transform_value' not in args:
            args['transform_value'] = default_transform_value
        metric_fct_map[name] = _build_metric_consumer_fct(**args)
    return metric_fct_map
