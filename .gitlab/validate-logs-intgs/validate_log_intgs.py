"""Python script to parse the logs pipeline from the logs-backend repository.
This script is expected to run from a CLI, do not import it."""
import sys
import json
from typing import List, Optional, Set  # noqa: F401
import re
import yaml
import os

LOGS_BACKEND_INTGS_ROOT = os.environ['LOGS_BACKEND_INTGS_ROOT']
INTEGRATIONS_CORE = os.environ['INTEGRATIONS_CORE_ROOT']

ERR_UNEXPECTED_LOG_COLLECTION_CAT = "The check does not have a log pipeline but defines 'log collection' in its manifest file."
ERR_UNEXPECTED_LOG_DOC = "The check does not have a log pipeline but defines a source in its README."
ERR_MISSING_LOG_COLLECTION_CAT = "The check has a log pipeline called but does not define 'log collection' in its manifest file."
ERR_MISSING_LOG_DOC = "The check has a log pipeline but does not document log collection in the README file."
ERR_MULTIPLE_SOURCES = "The check has a log pipeline but documents multiple sources as part of its README file."
ERR_NOT_DEFINED_WEB_UI = "The check has a log pipeline but does not have a corresponding entry defined in web-ui."

EXCEPTIONS = {
    'amazon-eks': [ERR_UNEXPECTED_LOG_COLLECTION_CAT], # eks is just a tile
    'aspdotnet': [ERR_MISSING_LOG_DOC], # Use iis pipeline
    'azure-active-directory': [
        ERR_MISSING_LOG_DOC,  # This is a tile only integration, the source is populated by azure directly.
        ERR_NOT_DEFINED_WEB_UI,  # The integration does not have any metrics.
    ],
    'cilium': [
        ERR_UNEXPECTED_LOG_COLLECTION_CAT,  # cilium does not need a pipeline to automatically parse the logs
        ERR_UNEXPECTED_LOG_DOC  # The documentation says to use 'source: cilium'
    ],
    'consul-connect': [ERR_MISSING_LOG_DOC], # Use envoy pipeline
    'docker': [ERR_UNEXPECTED_LOG_COLLECTION_CAT], # Tile only integration
    'ecs-fargate': [
        ERR_UNEXPECTED_LOG_COLLECTION_CAT, # Log collection but not from the agent
        ERR_UNEXPECTED_LOG_DOC, # Not collecting logs directly, but has example in its readme
    ],
    'eks-anywhere': [ERR_UNEXPECTED_LOG_COLLECTION_CAT], # Works with amazon_eks
    'eks-fargate': [ERR_UNEXPECTED_LOG_COLLECTION_CAT], # Log collection but not from the agent
    'fluentd': [ERR_UNEXPECTED_LOG_COLLECTION_CAT],  # Fluentd is about log collection but we don't collect fluentd logs
    'jmeter': [ERR_MISSING_LOG_DOC], # Tile only in integrations-core, logs collected in DataDog/jmeter-datadog-backend-listener
    'journald': [
        ERR_UNEXPECTED_LOG_DOC, # Journald is a type of logs, and has its own tile
        ERR_UNEXPECTED_LOG_COLLECTION_CAT,
    ],
    'kubernetes': [ERR_UNEXPECTED_LOG_COLLECTION_CAT],  # The agent collects logs from kubernetes environment but there is no pipeline per se
    'mesos-master': [ERR_UNEXPECTED_LOG_COLLECTION_CAT], # We do support log collection for mesos environments
    'linkerd': [
        ERR_UNEXPECTED_LOG_COLLECTION_CAT,  # linkerd does not need a pipeline to automatically parse the logs
        ERR_UNEXPECTED_LOG_DOC
    ],
    'openshift': [ERR_UNEXPECTED_LOG_COLLECTION_CAT],  # The agent collects logs from openshift environment but there is no pipeline
    'pan-firewall': [ERR_NOT_DEFINED_WEB_UI], # The integration doesn't emit metric
    'pivotal-pks': [ERR_UNEXPECTED_LOG_COLLECTION_CAT], # Using kubernetes pipeline
}


class CheckDefinition(object):
    """
    Represents a single check/integration for the agent, with all the various identifiers
    it may have.
    """
    def __init__(self, dir_name: str) -> None:
        """
        Creates the CheckDefinition instance by looking up all ids from the integration directory.
        Note: Does not populate log_source_name and is_defined_in_web_ui as they can't be retrieved
        from the integration folder.
        :param dir_name: The integration directory in the integrations-core repository
        """
        self.dir_name = dir_name

        with open(os.path.join(INTEGRATIONS_CORE, dir_name, "manifest.json"), 'r') as manifest:
            content = json.load(manifest)
            # name of the integration
            self.name: str = content['app_id']
            # boolean: whether or not the integration supports log collection
            self.log_collection: bool = 'Category::Log Collection' in content.get('tile', {}).get('classifier_tags', [])
            # boolean: whether or not the integration has public facing docs
            self.is_public: bool = content['display_on_public_website']
            # Log source defined in the manifest.json of the integration
            self.log_source: Optional[str] = content.get("assets", {}).get("logs", {}).get("source")

        # Whether or not this check has a log to metrics mapping defined in web-ui
        self.is_defined_in_web_ui: bool = False

        # All the log sources defined in the README (in theory only one or zero). Useful to alert if multiple sources
        # are defined in the README or if documentation is missing.
        self.source_names_readme: List[str] = self.get_log_sources_in_readme()

    def get_log_sources_in_readme(self) -> List[str]:
        """
        Parses the README file to find `source: ID`. This log source is supposed to be the same as the one
        defined in the logs pipeline.
        :return: A list of all sources found in the README. Usually one or zero.
        """
        readme_file = os.path.join(INTEGRATIONS_CORE, self.dir_name, "README.md")
        with open(readme_file, 'r') as f:
            content = f.read()

        code_sections: List[str] = re.findall(r'(```.*?```|`.*?`)', content, re.DOTALL)
        sources = set(re.findall(r'(?:"source"|source|\\"source\\"): \\?"?(\w+)\\?"?', "\n".join(code_sections), re.MULTILINE))

        return list(sources)

    def validate(self) -> List[str]:
        if not self.is_public:
            return []

        errors = set()
        if not self.log_source:
            # This check doesn't appear to have a log pipeline.
            if self.log_collection:
                errors.add(ERR_UNEXPECTED_LOG_COLLECTION_CAT)
            if self.source_names_readme:
                errors.add(ERR_UNEXPECTED_LOG_DOC)
        else:
            # This check has a log pipeline, let's validate it.
            if not self.log_collection:
                errors.add(ERR_MISSING_LOG_COLLECTION_CAT)
            if not self.source_names_readme:
                errors.add(ERR_MISSING_LOG_DOC)
            if len(self.source_names_readme) > 1:
                errors.add(ERR_MULTIPLE_SOURCES)
            if not self.is_defined_in_web_ui:
                errors.add(ERR_NOT_DEFINED_WEB_UI)

        # Filter out some expected edge cases:
        for exp_err in EXCEPTIONS.get(self.name, []):
            if exp_err in errors:
                errors.remove(exp_err)
        return list(errors)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, ", ".join(f"{k}={v}" for k, v in self.__dict__.items()))


def print_err(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def get_all_checks() -> List[CheckDefinition]:
    check_dirs = [
        d for d in os.listdir(INTEGRATIONS_CORE)
        if not d.startswith('.')
        and os.path.isfile(os.path.join(INTEGRATIONS_CORE, d, "manifest.json"))
    ]
    check_dirs.sort()

    all_checks = []
    for check_dir in check_dirs:
        all_checks.append(CheckDefinition(check_dir))

    return all_checks


def get_all_log_pipelines_ids():
    files = [os.path.join(LOGS_BACKEND_INTGS_ROOT, f) for f in os.listdir(LOGS_BACKEND_INTGS_ROOT)]
    files = [f for f in files if os.path.isfile(f)]
    files.sort()
    for file in files:
        with open(file, 'r') as f:
            yield yaml.load(f, Loader=yaml.SafeLoader)['id']


def get_log_to_metric_map(file_path):
    with open(file_path) as f:
        mapping = json.load(f)

    return {x['logSourceName']: x['metricsPrefixes'] for x in mapping if 'logSourceName' in x}


if len(sys.argv) != 2:
    print_err("This script requires a single JSON file as an argument.")
    sys.exit(1)

logs_to_metrics_mapping = get_log_to_metric_map(sys.argv[1])
assert len(logs_to_metrics_mapping) > 0

all_checks = list(get_all_checks())
assert len(all_checks) > 0
for check in all_checks:
    if check.log_source in logs_to_metrics_mapping:
        check.is_defined_in_web_ui = True

validation_errors_per_check = {}
for check in all_checks:
    errors = check.validate()
    if errors:
        validation_errors_per_check[check.name] = errors

if not validation_errors_per_check:
    print("Success, no errors were found!")
    sys.exit(0)

print_err("Logs pipelines don't pass validation steps:")
# Filter to only agt integrations checks
for check, errs in validation_errors_per_check.items():
    for err in errs:
        print_err(f"- {check}: {err}")
