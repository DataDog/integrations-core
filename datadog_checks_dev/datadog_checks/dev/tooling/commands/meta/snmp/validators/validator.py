from ..duplicate_metric_profile import verify_duplicate_metrics_profile_recursive

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

    def __repr__(self):
        return str(self.result)



class DoubleMetricsValidator(ProfileValidator):
    def validate(self, profile: str, directory: str, path: list) -> None:
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
            output_message = OID + " is duplicated in profiles: \n"
            for file, line in duplicated.get(OID):
                output_message = output_message + "|------> " + file + ":" + str(line) + '\n'
            self.fail(output_message)
        if len(duplicated) == 0:
            self.success("No duplicated OID ")
        


def get_all_validators():
    #type () -> list(ProfileValidator)
    return [
        DoubleMetricsValidator()
    ]