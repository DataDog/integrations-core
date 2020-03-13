from typing import TypeVar, Any, NewType

ManagedEntity = NewType('ManagedEntity', Any)  # type: ignore


MorType = NewType('MorType', Any)  # type: ignore
Counter = NewType('Counter', Any)  # type: ignore

# vim.PerformanceManager.QuerySpec
QuerySpec = NewType('QuerySpec', Any)  # type: ignore
# vim.PerformanceManager.MetricId
MetricId = NewType('MetricId', Any)  # type: ignore
