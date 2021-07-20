from datadog_checks.dev.tooling.constants import get_root
import click

import yaml
from yaml.loader import SafeLoader

from os.path import join

from ...console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success


@click.command("check-duplicates", short_help="Check SNMP profiles for duplicate metrics",  context_settings=CONTEXT_SETTINGS)
@click.option('-f', '--file', help="Path to a profile file to validate")
@click.option('-d', '--directory', help="Path to a directory of profiles to validate")
@click.option('-p', '--path', help="File containg the path of the directories of all profiles")
def check_duplicates(file, directory, path):
    """
    Calls the recursive function(verify_duplicate_metrics_profile_recursive) to check if there are any duplicated metric.
    It also logs the duplicated OID and reports all the files:lines where it is.
    """
    path = initialize_path(path, directory)
    used_metrics = {}
    duplicated = {}
    verify_duplicate_metrics_profile_recursive(
        file, used_metrics, duplicated, path)
    # print(duplicated)
    for OID in duplicated:
        echo_failure(OID + " is duplicated in profiles: ")
        for file, line in duplicated.get(OID):
            echo_failure("|------> "+file+":"+str(line))
    if len(duplicated) == 0:
        echo_success("No duplicated OID ")
    return duplicated

class SafeLineLoader(SafeLoader):

    def construct_mapping(self, node, deep=False):
        """
        Function to allow retrieving the line of the duplicated metric.\n
        It adds the key "__line__" with the value of the line it is to every key in the mapping created by yaml.load
        """
        mapping = super(SafeLineLoader, self).construct_mapping(
            node, deep=deep)
        # Add 1 so line numbering starts at 1
        mapping['__line__'] = node.start_mark.line + 1
        return mapping


def verify_duplicate_metrics_profile_recursive(file, used_metrics, duplicated, path):
    """
    Recursively for each profile extended, it checks the metrics and add them into the mapping "used_metrics".\n
    If the metric is duplicated, it also adds it to the mapping "duplicated".
    """
    extensions = verify_duplicate_metrics_profile_file(
        file, used_metrics, duplicated, path)
    if extensions:
        for file_name in extensions:
            verify_duplicate_metrics_profile_recursive(
                file_name, used_metrics, duplicated, path)


def verify_duplicate_metrics_profile_file(file, used_metrics, duplicated, path):
    # type: (any, dict, dict, list) -> list
    """
    Extract the OIDs of a profile and adds them to "used_metrics".\n
    The duplicated metrics are also added to "duplicated" mapping. "duplicated" is a dictionary where the OIDs are the keys and the values are lists of tuples (name_of_profile,line)
    """
    file_contents = find_profile_in_path(file,path)
    if not file_contents:
        print("File contents returned None: " + file)
        abort()
    # print(path)
    if file_contents.get('metrics'):
        for metric in file_contents.get('metrics'):
            # Check if there are symbols metrics
            if metric.get('symbols'):
                extract_oids_from_symbols(
                    metric, used_metrics, duplicated, file)
            # Check if there are symbol metrics
            if metric.get('symbol'):
                extract_oid_from_symbol(metric, used_metrics, duplicated, file)

    return file_contents.get('extends')


def extract_oids_from_symbols(metric, used_metrics, duplicated, file):
    """
    Function to extract OID from symbols
    """
    for metric_symbols in metric.get('symbols'):
        OID = metric_symbols.get('OID')
        line = metric_symbols.get('__line__')
        if OID not in used_metrics:
            used_metrics[OID] = [(file, line)]
        else:
            used_metrics[OID].append((file, line))
            duplicated[OID] = used_metrics[OID]


def extract_oid_from_symbol(metric, used_metrics, duplicated, file):
    """
    Function to extract OID from symbol
    """
    OID = metric.get('symbol').get('OID')
    line = metric.get('symbol').get('__line__')
    if OID not in used_metrics:
        used_metrics[OID] = [(file, line)]
    else:
        used_metrics[OID].append((file, line))
        duplicated[OID] = used_metrics[OID]

def initialize_path(path_name, directory):
    path = []
    if path_name:
        with open(path_name) as f:
            for directory_path in f:
                path.append(directory_path.strip())

    path.append(join(get_root(),
                     'snmp',
                     'datadog_checks',
                     'snmp',
                     'data',
                     'profiles'
                     ))

    if directory:
        path.append(directory)
    
    print(path)
    return path

def find_profile_in_path(profile_name, path):
    file_contents = None
    for directory_path in path:
        try:
            with open(join(directory_path, profile_name)) as f:
                file_contents = yaml.load(f.read(), Loader=SafeLineLoader)
        except:
            continue
        if file_contents:
            return file_contents
    return file_contents