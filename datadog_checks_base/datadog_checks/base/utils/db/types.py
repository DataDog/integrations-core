from typing import Any, Callable, Dict, Iterable, Sequence, Union

Transformer = Callable
TransformerFactory = Callable[[Dict[str, Transformer], str, Dict[str, Any]], Transformer]
QueriesExecutor = Callable[[str], Union[Sequence, Iterable]]
QueriesSubmitter = object
