import json
from posixpath import join

import jsonschema

from datadog_checks.dev.tooling.constants import get_root

from .utils import find_profile_in_path, get_all_profiles_directory, get_profile


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

    def validate(self, profile, path):
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
    """ "
    Validator responsible to check if the profile matches with the schemas.
    """

    def __init__(self):
        super(SchemaValidator, self).__init__()
        self.errors = []
        self.contents = None

    def __repr__(self):
        return self.file_path

    def load_from_file(self, file_path, path):
        self.contents = find_profile_in_path(file_path, path, line=False)
        if not self.contents:
            self.fail("File contents returned None: " + file_path)

    def validate(self, profile, path):
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
        self.load_from_file(profile, path)

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


class DuplicateOIDValidator(ProfileValidator):
    """ "
    Validator responsible to check if there are no duplicated oid in the profile.
    It checks all the profiles extended by the profile passed.
    """

    def __init__(self):
        super().__init__()
        self.used_oid = {}
        self.duplicated = {}

    def validate(self, profile, path):
        # type: (ProfileValidator,str, str) -> None
        """
        Calls the recursive function(verify_duplicate_oid_profile_recursive)
        to check if there are any duplicated oid.
        It also logs the duplicated OID and reports all the files:lines where it is.
        """
        self.verify_duplicate_oid_profile_recursive(profile, path)
        for OID in self.duplicated:
            output_message = ""
            output_message = "metric with OID " + OID + " is duplicated in profiles: \n"
            for file, line in self.duplicated.get(OID):
                output_message = output_message + "|------> " + file + ":" + str(line) + '\n'
            self.fail(output_message)
        if len(self.duplicated) == 0 and not self.result.failed:
            self.success("No duplicated OID ")

    def verify_duplicate_oid_profile_recursive(self, file, path):
        """
        Recursively for each profile extended, it checks the oid and add them into the mapping "used_oid".\n
        If the oid is duplicated, it also adds it to the mapping "duplicated".
        """
        extensions = self.verify_duplicate_oid_profile_file(file, path)
        if extensions:
            for file_name in extensions:
                self.verify_duplicate_oid_profile_recursive(file_name, path)

    def verify_duplicate_oid_profile_file(self, file, path):
        # type: (str, list) -> list
        """
        Extract the OIDs of a profile and adds them to "used_oid".\n
        The duplicated oid are also added to "duplicated" mapping. \n
        "duplicated" is a dictionary where the OIDs are the keys and
        the values are lists of tuples (name_of_profile,line)
        """
        file_contents = find_profile_in_path(file, path)
        if not file_contents:
            self.fail("File contents returned None: " + file)
            return
        # print(path)
        if file_contents.get('metrics'):
            for metric in file_contents.get('metrics'):
                # Check if there are symbols metrics
                if metric.get('symbols'):
                    self.extract_oids_from_symbols(metric, file)
                # Check if there are symbol metrics
                if metric.get('symbol'):
                    self.extract_oid_from_symbol(metric, file)

        return file_contents.get('extends')

    def extract_oids_from_symbols(self, metric, file):
        """
        Function to extract OID from symbols
        """
        for metric_symbols in metric.get('symbols'):
            OID = metric_symbols.get('OID')
            line = metric_symbols.get('__line__')
            if OID not in self.used_oid:
                self.used_oid[OID] = [(file, line)]
            else:
                self.used_oid[OID].append((file, line))
                self.duplicated[OID] = self.used_oid[OID]

    def extract_oid_from_symbol(self, metric, file):
        """
        Function to extract OID from symbol
        """
        OID = metric.get('symbol').get('OID')
        # Check if the metric is a flag_stream
        if (
            metric.get('forced_type') == 'flag_stream'
            and metric.get('options')
            and metric.get('options').get('metric_suffix')
        ):
            # if it is a flag stream, do the hash as: OID.placement
            # e.g OID = 1.2.3 and placement = 9 -> hash with 1.2.3.9
            OID = OID + '.' + str(metric.get('options').get('placement'))
        line = metric.get('symbol').get('__line__')
        if OID not in self.used_oid:
            self.used_oid[OID] = [(file, line)]
        else:
            self.used_oid[OID].append((file, line))
            self.duplicated[OID] = self.used_oid[OID]


class SysobjectidValidator(ProfileValidator):
    """
    Validator responsible to check if there are no duplicated sysobjectid in the profile.
    """

    def __init__(self):
        super().__init__()
        self.used_sysobjid = {}
        self.duplicated = {}
        self.seen_profiles = {}

    def validate(self, profile, path):
        sysobjectids = self.extract_sysobjectids_profile(profile)
        self.check_sysobjectids_are_duplicated(sysobjectids, profile)
        for directory in path:
            for profile in get_all_profiles_directory(directory):
                sysobjectids = self.extract_sysobjectids_profile(profile)
                self.check_sysobjectids_are_duplicated(sysobjectids, profile)
        self.report_errors()

    def report_errors(self):
        if len(self.duplicated) == 0:
            self.success("No duplicated sysobjectid")
        else:
            for sysobjectid in self.duplicated:
                error_message = "SysObjectId {} is duplicated in:\n".format(sysobjectid)
                for profile in self.duplicated[sysobjectid]:
                    error_message = error_message + "|------> {}\n".format(profile)
                self.fail(error_message)

    def extract_sysobjectids_profile(self, profile):
        file_contents = get_profile(profile)
        if not file_contents:
            return []
        sysobjectid = file_contents.get('sysobjectid')
        if (not isinstance(sysobjectid, list)) and sysobjectid:
            sysobjectid = [sysobjectid]
        return sysobjectid

    def check_sysobjectids_are_duplicated(self, sysobjectids, profile):
        if (not sysobjectids) or (profile in self.seen_profiles):
            return
        self.seen_profiles[profile] = True
        for sysobjectid in sysobjectids:
            if sysobjectid not in self.used_sysobjid:
                self.used_sysobjid[sysobjectid] = [profile]
            else:
                self.used_sysobjid[sysobjectid].append(profile)
                self.duplicated[sysobjectid] = self.used_sysobjid[sysobjectid]


def get_all_single_validators():
    # type () -> list(ProfileValidator)
    return [SchemaValidator(), DuplicateOIDValidator()]


def get_all_group_validators():
    # type () -> list(ProfileValidator)
    return [SysobjectidValidator()]
