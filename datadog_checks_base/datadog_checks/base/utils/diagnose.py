# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
 
"""
defined in
    datadog-agent\pkg\diagnose\diagnosis\loader.go and 


// Use explicit constant instead of iota because the same numbers are used
// in Python/CGO calls.
const (
	DiagnosisSuccess         DiagnosisResult = 0
	DiagnosisNotEnable       DiagnosisResult = 1
	DiagnosisFail            DiagnosisResult = 2
	DiagnosisWarning         DiagnosisResult = 3
	DiagnosisUnexpectedError DiagnosisResult = 4
	DiagnosisResultMIN                       = DiagnosisSuccess
	DiagnosisResultMAX                       = DiagnosisUnexpectedError
)
"""
DIAGNOSIS_SUCCESS = 0
DIAGNOSIS_NOT_ENABLE = 1
DIAGNOSIS_FAIL = 2
DIAGNOSIS_WARNING = 3
DIAGNOSIS_UNEXPECTED_ERROR = 4
DIAGNOSIS_RESULT_MAX = DIAGNOSIS_UNEXPECTED_ERROR

class Diagnosis(object):
    """
    Class encapsulated Agent's 
        // Diagnose result (diagnosis)
        type Diagnosis struct {
            // --------------------------
            // required fields

            // run-time (pass, fail etc)
            Result DiagnosisResult
            // static-time (meta typically)
            Name string
            // run-time (actual diagnosis consumable by a user)
            Diagnosis string

            // --------------------------
            // optional fields

            // static-time (meta typically)
            Category string
            // static-time (meta typically, description of what being tested)
            Description string
            // run-time (what can be done of what docs need to be consulted to address the issue)
            Remediation string
            // run-time
            RawError error
        }

    defined in datadog-agent\pkg\diagnose\diagnosis\loader.go

    The list of this class instances is used as return value of check instance
    get_diagnoses() method. By default base get_diagnoses() class returns empty
    list (see integrations-core\datadog_checks_base\datadog_checks\base\checks\base.py)
    """

    def __init__(self, result, name, diagnosis, category=None, description=None, remedeition=None, raw_error=None):
        # Required fields
        self.result = result        # e.g. DIAGNOSIS_SUCCESS, DIAGNOSIS_FAIL
        self.name = name            # short diagnosis name
        self.diagnosis = diagnosis  # actual diangosis string

        # Optional fields
        self.category = category        # category of the diagnosis (e.g DBM)
        self.description = description  # description of this particular diagnose test
        self.remedeition = remedeition  # if available potential steps to fix the problem and or reference to the documentation
        self.raw_error = raw_error      # actual error reported by diagnose method
