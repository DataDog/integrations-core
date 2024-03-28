# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from operator import itemgetter

from datadog_checks.base.utils.diagnose import Diagnosis


def test_no_diagnosis_when_no_certificates_are_specified(instance, check):
    mongo_check = check(instance)
    diagnoses = json.loads(mongo_check.get_diagnoses())
    assert len(diagnoses) == 0


def test_certificate_files_success(instance, check, tmp_path):
    certificate_key_path = tmp_path / 'client.pem'
    ca_path = tmp_path / 'ca.pem'

    # Create dummy certificate files
    certificate_key_path.touch()
    ca_path.touch()

    instance['tls_certificate_key_file'] = str(certificate_key_path)
    instance['tls_ca_file'] = str(ca_path)

    mongo_check = check(instance)
    diagnoses = sorted(json.loads(mongo_check.get_diagnoses()), key=itemgetter('diagnosis'))
    assert len(diagnoses) == 2
    assert diagnoses[0]['result'] == Diagnosis.DIAGNOSIS_SUCCESS
    assert str(ca_path) in diagnoses[0]['diagnosis']
    assert diagnoses[1]['result'] == Diagnosis.DIAGNOSIS_SUCCESS
    assert str(certificate_key_path) in diagnoses[1]['diagnosis']


def test_certificate_files_failure_not_exist(instance, check, tmp_path):
    certificate_key_path = tmp_path / 'client.pem'
    ca_path = tmp_path / 'ca.pem'

    instance['tls_certificate_key_file'] = str(certificate_key_path)
    instance['tls_ca_file'] = str(ca_path)

    mongo_check = check(instance)
    diagnoses = sorted(json.loads(mongo_check.get_diagnoses()), key=itemgetter('diagnosis'))
    assert len(diagnoses) == 2
    assert diagnoses[0]['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert str(ca_path) in diagnoses[0]['diagnosis']
    assert "does not exist" in diagnoses[0]['diagnosis']
    assert diagnoses[1]['result'] == Diagnosis.DIAGNOSIS_FAIL
    assert str(certificate_key_path) in diagnoses[1]['diagnosis']
    assert "does not exist" in diagnoses[1]['diagnosis']
