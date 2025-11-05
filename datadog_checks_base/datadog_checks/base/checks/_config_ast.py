import ast
from enum import Enum
from typing import Any

# This module is used to parse and modify the config AST before it is loaded.
# It is used to handle special float values (inf, -inf, nan) and replace them with placeholders since those
# are not valid Python literals.


class SpecialFloatPlaceholder(str, Enum):
    INF = '__PYTHON_INF__'
    NEG_INF = '__PYTHON_NEG_INF__'
    NAN = '__PYTHON_NAN__'


class _SpecialFloatValuesTransformer(ast.NodeTransformer):
    def visit_Name(self, node: ast.Name) -> ast.AST:
        """
        Processes named constants like 'inf' and 'nan'.
        If the name is 'inf', it's replaced with a placeholder for positive infinity.
        If the name is 'nan', it's replaced with a placeholder for Not a Number.
        Other names are returned unchanged.
        """
        if node.id == 'inf':
            return ast.Constant(value=SpecialFloatPlaceholder.INF.value)
        elif node.id == 'nan':
            return ast.Constant(value=SpecialFloatPlaceholder.NAN.value)
        return node  # Leaf node, no children to visit

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
        """
        Processes unary operations like negation.
        If the operation is a negation ('-') applied to the name 'inf',
        it's replaced with a placeholder for negative infinity.
        We can't use visit_Name for this because the constant is 'inf' and not '-inf'.
        Other unary operations are processed as normal.
        """
        if isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Name) and node.operand.id == 'inf':
            return ast.Constant(value=SpecialFloatPlaceholder.NEG_INF.value)
        return self.generic_visit(node)


def _restore_special_floats(data: Any) -> Any:
    """
    Restores placeholders for special float values (inf, -inf, nan) to their actual
    float values in a nested data structure.
    """
    if isinstance(data, dict):
        return {key: _restore_special_floats(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_restore_special_floats(item) for item in data]
    elif isinstance(data, str):
        if data == SpecialFloatPlaceholder.INF.value:
            return float('inf')
        elif data == SpecialFloatPlaceholder.NEG_INF.value:
            return float('-inf')
        elif data == SpecialFloatPlaceholder.NAN.value:
            return float('nan')
    return data


def parse(object_string: str) -> Any:
    """
    Parses a printed Python object, handling special float values (inf, -inf, nan).
    If any error occurs, the original string is returned.
    """
    try:
        if not object_string:
            return None

        # Parse the string as a Python expression
        ast_node = ast.parse(object_string, mode='eval').body

        # Replace inf/nan with placeholders
        transformer = _SpecialFloatValuesTransformer()
        transformed_ast_node = transformer.visit(ast_node)

        # Evaluate the AST node to get the actual value.
        data_with_placeholders = ast.literal_eval(transformed_ast_node)

        # Restore placeholders to actual float values
        return _restore_special_floats(data_with_placeholders)
    except Exception:
        return object_string
