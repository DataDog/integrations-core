import json
import jsonschema

from datadog_checks.dev.tooling.constants import get_root
from posixpath import join
from ..duplicate_metric_profile import verify_duplicate_metrics_profile_recursive
from ....console import abort

from .utils import (
    find_profile_in_path,
)

class ValidationResult(object):
    def __init__(self):
        self.failed = False
        self.fixed = False
        self.messages = {'success': [], 'warning': [], 'failure': [], 'info': []}

    def __str__(self):
        return '\n'.join(['\n'.join(messages) for messages in self.messages.values()])

    def __repr__(self):
        return str(self)


class ProfileValidator(object):
    """
    Class that will be subclassed to create the validators for the profile.
    """
    def __init__(self):
        self.result = ValidationResult()

    def validate(self, profile, directory, path):
        # type: (str, str, list(str)) -> None
        raise NotImplementedError

    def fail(self, error_message):
        self.result.failed = True
        self.result.messages['failure'].append(error_message)

    def fix(self, problem, solution):
        self.result.warning_msg = problem
        self.result.success_msg = solution
        self.result.fixed = True
        self.result.failed = False

    def success(self, success_message):
        self.result.messages['success'].append(success_message)
    
    def info(self, info_message):
        self.result.messages['info'].append(info_message)
    
    def warning(self, warning_message):
        self.result.messages['warning'].append(warning_message)

    def __repr__(self):
        return str(self.result)

class SchemaValidator(ProfileValidator):
    """"
    Validator responsible to check if the profile matches with the schemas.
    """
    def __init__(self):
        super(SchemaValidator, self).__init__()
        self.errors = []
        self.contents = None

    def __repr__(self):
        return self.file_path

    def load_from_file(self, file_path,path):
        self.contents = find_profile_in_path(file_path,path, line = False)
        if not self.contents:
            self.fail("File contents returned None: " + file_path)
            

    def validate(self, profile: str, directory: str, path: list):
        schema_file = join(
            get_root(),
            "datadog_checks_dev",
            "datadog_checks",
            "dev",
            "tooling",
            "commands",
            "meta",
            "snmp",
            "validators",
            "profile_schema.json",
        )
        self.load_from_file(profile,path)

        with open(schema_file, "r") as f:
            contents = f.read()
            schema = json.loads(contents)
        validator = jsonschema.Draft7Validator(schema)

        errors = validator.iter_errors(self.contents)
        for error in errors:
            self.errors.append(error)
            self.fail(error.message)
        
        if len(self.errors) == 0:
            self.success("Schema successfully validated")

class DuplicateMetricsValidator(ProfileValidator):
    """"
    Validator responsible to check if there are no duplicated metrics in the profile.
    It checks all the profiles extended by the profile passed.
    """
    def validate(self, profile, directory, path):
        #type: (ProfileValidator,str, str, str) -> None
        """
        Calls the recursive function(verify_duplicate_metrics_profile_recursive) to check if there are any duplicated metric.
        It also logs the duplicated OID and reports all the files:lines where it is.
        """
        used_metrics = {}
        duplicated = {}
        verify_duplicate_metrics_profile_recursive(
            profile, used_metrics, duplicated, path)
        for OID in duplicated:
            output_message = ""
            output_message = "metric with OID " + OID + " is duplicated in profiles: \n"
            for file, line in duplicated.get(OID):
                output_message = output_message + "|------> " + file + ":" + str(line) + '\n'
            self.fail(output_message)
        if len(duplicated) == 0:
            self.success("No duplicated OID ")
        


def get_all_validators():
    #type () -> list(ProfileValidator)
    return [
        SchemaValidator(),
        DuplicateMetricsValidator()
    ]