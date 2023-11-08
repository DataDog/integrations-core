# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections import namedtuple


class Diagnosis:
    """
    A class used to register explicit diagnostics and record diagnoses on integrations.
    """

    # // Diagnose result (diagnosis)
    # type Diagnosis struct {
    #     // --------------------------
    #     // required fields

    #     // run-time (pass, fail etc)
    #     Result DiagnosisResult
    #     // static-time (meta typically)
    #     Name string
    #     // run-time (actual diagnosis consumable by a user)
    #     Diagnosis string

    #     // --------------------------
    #     // optional fields

    #     // static-time (meta typically)
    #     Category string
    #     // static-time (meta typically, description of what being tested)
    #     Description string
    #     // run-time (what can be done of what docs need to be consulted to address the issue)
    #     Remediation string
    #     // run-time
    #     RawError error
    # }
    # defined in datadog-agent\\pkg\\diagnose\\diagnosis\\loader.go
    Result = namedtuple('Result', ['result', 'name', 'diagnosis', 'category', 'description', 'remediation', 'rawerror'])

    # defined in
    # datadog-agent\\pkg\\diagnose\\diagnosis\\loader.go and
    # datadog-agent\\rtloader\\include\\rtloader_types.h
    DIAGNOSIS_SUCCESS = 0
    DIAGNOSIS_FAIL = 1
    DIAGNOSIS_WARNING = 2
    DIAGNOSIS_UNEXPECTED_ERROR = 3

    def __init__(self, sanitize=None):
        # Holds results
        self._diagnoses = []
        # Holds explicit diagnostic routines (callables)
        self._diagnostics = []
        # Sanitization function
        if sanitize is not None:
            # We need to account for a field being `None`, with the sanitizer might not do
            self._sanitize = lambda t: t and sanitize(t)
        else:
            self._sanitize = lambda t: t

    def clear(self):
        """Remove all cached diagnoses."""
        self._diagnoses = []

    def success(self, name, diagnosis, category=None, description=None, remediation=None, rawerror=None):
        """Register a successful diagnostic result."""
        self._diagnoses.append(
            self._result(
                self.DIAGNOSIS_SUCCESS,
                name,
                diagnosis=diagnosis,
                category=category,
                description=description,
                remediation=remediation,
                rawerror=rawerror,
            )
        )

    def fail(self, name, diagnosis, category=None, description=None, remediation=None, rawerror=None):
        """Register a failing diagnostic result."""
        self._diagnoses.append(
            self._result(
                self.DIAGNOSIS_FAIL,
                name,
                diagnosis,
                category=category,
                description=description,
                remediation=remediation,
                rawerror=rawerror,
            )
        )

    def warning(self, name, diagnosis, category=None, description=None, remediation=None, rawerror=None):
        """Register a warning for a diagnostic result."""
        self._diagnoses.append(
            self._result(
                self.DIAGNOSIS_WARNING,
                name,
                diagnosis,
                category=category,
                description=description,
                remediation=remediation,
                rawerror=rawerror,
            )
        )

    def register(self, *diagnostics):
        """Register one or many explicit diagnostic functions.

        Diagnostic functions are called when diagnoses are requested by the agent to the integration via
        the base check's `get_diagnoses()` function. They are called in the order of registration."""
        self._diagnostics.extend(diagnostics)

    def run_explicit(self):
        """Run registered explicit diagnostics and return their results.

        Diagnosis results produced within this function will not be stored in the `Diagnosis` object.
        Exceptions raised within explicit diagnostic functions will be caught and returned as a special diagnose
        of type `DIAGNOSIS_UNEXPECTED_ERROR`.
        """
        # Keep a reference to existing cached results, to be restored at the end,
        # and start from an empty list to collect explicit diagnoses (to be returned later)
        cached_results, self._diagnoses = self._diagnoses, []
        for diagnostic in self._diagnostics:
            try:
                diagnostic()
            except Exception as e:
                self._diagnoses.append(self._result(self.DIAGNOSIS_UNEXPECTED_ERROR, "", "", rawerror=str(e)))

        explicit_results, self._diagnoses = self._diagnoses, cached_results
        return explicit_results

    @property
    def diagnoses(self):
        """The list of cached diagnostics."""
        return self._diagnoses

    def _result(self, result, name, diagnosis, category=None, description=None, remediation=None, rawerror=None):
        return self.Result(
            result,
            name,
            diagnosis,
            category,
            self._sanitize(description),
            self._sanitize(remediation),
            self._sanitize(rawerror),
        )
