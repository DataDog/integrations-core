# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json

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
    assert get_diagnoses(check) == [
        diagnose_dict(Diagnosis.DIAGNOSIS_FAIL, "foo check", "explicit diagnosis"),
    ]

    check.run()
    assert get_diagnoses(check) == [
        diagnose_dict(Diagnosis.DIAGNOSIS_SUCCESS, "foo check", "in-check diagnosis", None, None, None, None),
        diagnose_dict(Diagnosis.DIAGNOSIS_FAIL, "foo check", "explicit diagnosis", None, None, None, None),
    ]

    # A second run should give us the same results, meaning we get a fresh set of diagnoses
    # from the check run.
    check.run()
    assert get_diagnoses(check) == [
        diagnose_dict(Diagnosis.DIAGNOSIS_SUCCESS, "foo check", "in-check diagnosis", None, None, None, None),
        diagnose_dict(Diagnosis.DIAGNOSIS_FAIL, "foo check", "explicit diagnosis", None, None, None, None),
    ]


def test_exceptions_during_explicit_diagnoses_are_converted_into_unexpected_errors():
    class Foo(AgentCheck):
        def __init__(self, name, init_config, instances):
            super(Foo, self).__init__(name, init_config, instances)

            self.diagnosis.register(self.bad_diagnostic, self.good_diagnostic)

        def check(self, _):
            self.diagnosis.success("foo check", "in-check diagnosis")

        def bad_diagnostic(self):
            raise Exception("something went wrong")

        def good_diagnostic(self):
            self.diagnosis.success("foo check", "explicit diagnosis")

    check = Foo("foo", {}, [{}])
    check.run()

    assert get_diagnoses(check) == [
        diagnose_dict(Diagnosis.DIAGNOSIS_SUCCESS, "foo check", "in-check diagnosis", None, None, None, None),
        diagnose_dict(Diagnosis.DIAGNOSIS_UNEXPECTED_ERROR, "", "", None, None, None, "something went wrong"),
        diagnose_dict(Diagnosis.DIAGNOSIS_SUCCESS, "foo check", "explicit diagnosis", None, None, None, None),
    ]


def test_diagnose_fields_get_sanitized():
    fields_with_secrets = {
        "description": "something's wrong with your secret",
        "remediation": "change your secret to something else",
    }

    class Foo(AgentCheck):
        def __init__(self, name, init_config, instances):
            super(Foo, self).__init__(name, init_config, instances)

            self.diagnosis.register(self.bad_diagnostic)
            self.register_secret("secret")

        def check(self, _):
            self.diagnosis.success("foo check", "ok", **fields_with_secrets)
            self.diagnosis.fail("foo check", "fail", **fields_with_secrets)
            self.diagnosis.warning("foo check", "warn", **fields_with_secrets)

        def bad_diagnostic(self):
            raise Exception("something went wrong with secret")

    check = Foo("foo", {}, [{}])
    check.run()

    expected_fields = {
        "category": None,
        "description": "something's wrong with your ********",
        "remediation": "change your ******** to something else",
        "rawerror": None,
    }

    assert get_diagnoses(check) == [
        diagnose_dict(Diagnosis.DIAGNOSIS_SUCCESS, "foo check", "ok", **expected_fields),
        diagnose_dict(Diagnosis.DIAGNOSIS_FAIL, "foo check", "fail", **expected_fields),
        diagnose_dict(Diagnosis.DIAGNOSIS_WARNING, "foo check", "warn", **expected_fields),
        diagnose_dict(
            Diagnosis.DIAGNOSIS_UNEXPECTED_ERROR, "", "", None, None, None, "something went wrong with ********"
        ),
    ]


def get_diagnoses(check):
    """Get diagnoses from a check as a list of dictionaries."""
    return json.loads(check.get_diagnoses())


def diagnose_dict(result, name, diagnosis, category=None, description=None, remediation=None, rawerror=None):
    """Helper function to create diagnosis result dictionaries with defaults."""
    return {
        "result": result,
        "name": name,
        "diagnosis": diagnosis,
        "category": category,
        "description": description,
        "remediation": remediation,
        "rawerror": rawerror,
    }
