# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from dataclasses import dataclass, field


@dataclass(frozen=True, kw_only=True)
class TableConfig:
    name: str
    conditions: list[tuple[str, str, str | int | float]] = field(default_factory=list)
    conditional_operator: str = "AND"
    group_by: list[str] = field(default_factory=lambda: ["ClassName"])

    def __post_init__(self):
        # Validating dataclass members
        conditional_operators = ["AND", "OR"]
        if self.conditional_operator and self.conditional_operator not in conditional_operators:
            raise ValueError(
                f"Conditional operator must be one of {conditional_operators}, got {self.conditional_operator}."
            )

        comparison_operators = ["=", "<", ">", "<=", ">=", "<>", "!="]
        for condition in self.conditions:
            if not isinstance(condition, tuple) or len(condition) != 3:
                raise ValueError(
                    f"Each condition must be a tuple of 3 elements: (field, comparison_operator, value),"
                    f" got {condition}"
                )

            _, comparison_operator, value = condition
            if comparison_operator not in comparison_operators:
                raise ValueError(
                    f"Comparison operator must be one of '{comparison_operators}' in condition {condition}, "
                    f"got {comparison_operator}."
                )

            if not isinstance(value, (str | int | float)):
                raise ValueError(
                    f"Condition value must be of type str, int, or float, got {type(value)} for {condition}."
                )
