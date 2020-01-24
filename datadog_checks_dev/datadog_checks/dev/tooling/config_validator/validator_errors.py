# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
SEVERITY_ERROR = 0
SEVERITY_WARNING = 1


class ValidatorError:
    def __init__(self, error_str, line_number, severity=SEVERITY_ERROR):
        self.error_str = error_str
        self.severity = severity
        self.line_number = line_number

    def __repr__(self):
        if self.line_number is None:
            return self.error_str
        return f"(L{self.line_number + 1}) {self.error_str}"

    def __str__(self):
        return self.__repr__()
