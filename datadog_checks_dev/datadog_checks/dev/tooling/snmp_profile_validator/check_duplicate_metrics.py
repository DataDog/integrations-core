from collections import Counter

import click
import yaml

from ..constants import get_root
from ..commands.console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success
from ...fs import file_exists

#from ....snmp.datadog_checks.snmp.utils import get_profile_definition


@click.command("check-duplicates", short_help="Check SNMP profiles for duplicate metrics", context_settings=CONTEXT_SETTINGS)
@click.option('-f', '--file', help="Path to a profile file to validate")
# @click.option('-d', '--directory', help="Path to a directory of profiles to validate")
@click.option('-v', '--verbose', help="Increase verbosity of error messages", is_flag=True)

#imports?
# treat table and oid metrics separately?

#keep track of extends files - don't validate them twice

#open file
#extract extended profiles
# extract metrics
# compare for duplicates


#are the metrics i'm looking at correct?
# chain of validators



def check_duplicate_metrics(file, verbose):
    if not file_exists(file):
        echo_failure("File " + file + " not found, or could not be read")
        abort()

    profile = create_profile(file)
    find_duplicates(profile)


class Profile:
    def __init__(self):
        self.extends = []
        self.metrics = {}
        self.path = ""
        self.has_duplicates = False
    def __repr__(self):
        return self.path

def get_file(file):
    with open(file) as f:
        return yaml.safe_load(f)
#{'extends': ['_base.yaml', '_generic-if.yaml'], 'metrics': [{'MIB': 'HOST-RESOURCES-MIB', 'table': {'name': 'hrSWRunPerfTable', 'OID': '1.3.6.1.2.1.25.5.1'}, 'symbols': [{'name': 'hrSWRunPerfMem', 'OID': '1.3.6.1.2.1.25.5.1.1.2'}, {'name': 'hrSWRunPerfCPU', 'OID': '1.3.6.1.2.1.25.5.1.1.1'}], 'metric_tags': [{'column': {'name': 'hrSWRunIndex', 'OID': '1.3.6.1.2.1.25.4.2.1.1'}, 'table': 'hrSWRunTable', 'tag': 'run_index'}]}]}

def create_profile(file):
    profile = Profile()
    profile.path = file
    config = get_file(file)
    profile.metrics[profile.path] = config['metrics']
    profile.extends = config['extends']
    extended_profiles = extract_extended_profiles(file)
    profile.metrics = profile.metrics.update(extended_profiles)
    import pdb; pdb.set_trace()
    return profile
#why is profile.metrics coming up empty?


def extract_extended_profiles(file):
    extended_metrics = {}
    config = get_file(file)
    extended_metrics[file] = config['metrics']
    try:
        for file in config['extends']:
            profile.metrics[file] = config['metrics']
            extract_extended_profiles(file)
    except KeyError:
        echo_failure("KeyError")
    return extended_metrics


# def check_duplicates(profile):
#     def do_check_duplicates(profile, oids):


    #hidden function in recursion
    # get profiles at top of tree, add metrics to set
    # find loops
    #symbol and metrics - ignore table top OIDs



    # function to extract oids from profile
    # set of visited profiles
    # set of seen oids







# depth-first search
#set of seen

# collections.counter on OIDs? - just use strings to compare OIDs

def compare_for_duplicates(profile):
    #collections.counter?
    pass

#break recursion on IndexError

#make giant structure of metrics then check for duplicate oids - from root profile and extended profiles

    #why does this not work?
    # for metric in profile.metrics:
    #     for value in profile.extended_metrics.values():
    #         if metric == value:
    #             echo_info(metric)





# {'MIB': 'CISCO-ENTITY-SENSOR-MIB', 'table': {'OID': '1.3.6.1.4.1.9.9.91.1.1.1', 'name': 'entSensorValueTable'}}
# {'MIB': 'CISCO-ENTITY-SENSOR-MIB', 'table': {'OID': '1.3.6.1.4.1.9.9.91.1.1.1', 'name': 'entSensorValueTable'}}
# {'MIB': 'CISCO-ENTITY-SENSOR-MIB', 'table': {'OID': '1.3.6.1.4.1.9.9.91.1.1.1', 'name': 'entSensorValueTable'}}
# {'MIB': 'PAN-COMMON-MIB', 'symbol': {'OID': '1.3.6.1.4.1.25461.2.1.2.3.1.0', 'name': 'panSessionUtilization'}}
# {'MIB': 'PAN-COMMON-MIB', 'symbol': {'OID': '1.3.6.1.4.1.25461.2.1.2.3.2.0', 'name': 'panSessionMax'}}
# {'MIB': 'PAN-COMMON-MIB', 'symbol': {'OID': '1.3.6.1.4.1.25461.2.1.2.3.3.0', 'name': 'panSessionActive'}}




def find_duplicates(profile):
    echo_info(profile.metrics)
# metrics need to be associated with their filenames
# Counter like object that can keep the metric-filename link




#collections.Counter(a).items() if count > 1]

def report_duplicates(profile):
    # duplicate metric oid and files it is defined in, line no?
    pass






