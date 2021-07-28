from typing import Callable, Dict, Any

Transformer = Callable
TransformerFactory = Callable[[Dict[str, Transformer], str, Dict[str, Any]], Transformer]
