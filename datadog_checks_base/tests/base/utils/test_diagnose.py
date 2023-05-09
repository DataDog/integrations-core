# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.diagnose import Diagnosis


def test_recording_and_retrieving_diagnosis_results():
    diag = Diagnosis()
    diag.success("successful diagnosis", "diag a")
    diag.fail("failing diagnosis", "diag b")
    diag.warning("warning diagnosis", "diag c")

    assert diag.diagnoses == [
        Diagnosis.Result(Diagnosis.DIAGNOSIS_SUCCESS, "successful diagnosis", "diag a", None, None, None, None),
        Diagnosis.Result(Diagnosis.DIAGNOSIS_FAIL, "failing diagnosis", "diag b", None, None, None, None),
        Diagnosis.Result(Diagnosis.DIAGNOSIS_WARNING, "warning diagnosis", "diag c", None, None, None, None),
    ]

    diag.clear()
    assert not diag.diagnoses


def test_registering_and_running_explicit_diagnostics():
    diag = Diagnosis()

    def foo_diagnostic():
        diag.fail("foo", "a")

    def bar_diagnostic():
        diag.success("bar", "b")

    diag.register(foo_diagnostic, bar_diagnostic)

    my_results = diag.run_explicit()
    assert my_results == [
        Diagnosis.Result(Diagnosis.DIAGNOSIS_FAIL, "foo", "a", None, None, None, None),
        Diagnosis.Result(Diagnosis.DIAGNOSIS_SUCCESS, "bar", "b", None, None, None, None),
    ]

    # Explicit diagnostics must not be stored
    assert not diag.diagnoses


def test_check_subclasses_reporting_diagnoses():
    # Testing the full diagnose functionality end to end, from the agent's perspective
    class Foo(AgentCheck):
        def __init__(self, name, init_config, instances):
            super(Foo, self).__init__(name, init_config, instances)

            self.diagnosis.register(self.explicit_diagnostic)

        def check(self, _):
            self.diagnosis.success("foo check", "in-check diagnosis")

        def explicit_diagnostic(self):
            self.diagnosis.fail("foo check", "explicit diagnosis")

    check = Foo("foo", {}, [{}])

    # When the check hasn't yet run once, we should only see the explicit diagnostic results
    assert check.get_diagnoses() == [
        Diagnosis.Result(Diagnosis.DIAGNOSIS_FAIL, "foo check", "explicit diagnosis", None, None, None, None),
    ]

    check.run()
    assert check.get_diagnoses() == [
        Diagnosis.Result(Diagnosis.DIAGNOSIS_SUCCESS, "foo check", "in-check diagnosis", None, None, None, None),
        Diagnosis.Result(Diagnosis.DIAGNOSIS_FAIL, "foo check", "explicit diagnosis", None, None, None, None),
    ]

    # A second run should give us the same results, meaning we get a fresh set of diagnoses
    # from the check run.
    check.run()
    assert check.get_diagnoses() == [
        Diagnosis.Result(Diagnosis.DIAGNOSIS_SUCCESS, "foo check", "in-check diagnosis", None, None, None, None),
        Diagnosis.Result(Diagnosis.DIAGNOSIS_FAIL, "foo check", "explicit diagnosis", None, None, None, None),
    ]
