from typing import Any, Callable, Dict, Iterable, Sequence, Union

Transformer = Callable
TransformerFactory = Callable[[Dict[str, Transformer], str, Dict[str, Any]], Transformer]
QueryExecutor = Callable[[str], Union[Sequence, Iterable]]
