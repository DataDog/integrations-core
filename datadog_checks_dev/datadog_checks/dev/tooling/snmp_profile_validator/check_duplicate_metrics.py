

import click
import yaml

from ..constants import get_root
from ..commands.console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

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


def check_duplicate_metrics(file, verbose):
    m = create_profile(file)
    #extract_extended_profiles(m)


class Profile:
    def __init__(self):
        self.extends = []
        self.metrics = []
        self.extended_metrics = {} # file path : metrics
        self.path = ""
        self.has_duplicates = False
    def __repr__(self):
        return self.path

def get_file(file):
      with open(file) as f:
        return yaml.safe_load(f)
# {'extends': ['_base.yaml', '_generic-if.yaml'], 'metrics': [{'MIB': 'HOST-RESOURCES-MIB', 'table': {'name': 'hrSWRunPerfTable', 'OID': '1.3.6.1.2.1.25.5.1'}, 'symbols': [{'name': 'hrSWRunPerfMem', 'OID': '1.3.6.1.2.1.25.5.1.1.2'}, {'name': 'hrSWRunPerfCPU', 'OID': '1.3.6.1.2.1.25.5.1.1.1'}], 'metric_tags': [{'column': {'name': 'hrSWRunIndex', 'OID': '1.3.6.1.2.1.25.4.2.1.1'}, 'table': 'hrSWRunTable', 'tag': 'run_index'}]}]}

def create_profile(file):
    profile = Profile()
    profile.path = file
    config = get_file(file)
    profile.metrics = config['metrics']
    profile.extends = config['extends']
    for file in profile.extends:
        extended_profiles = extract_extended_profiles(file)
        echo_info("extended profile" + str(extended_profiles))
    return profile



def extract_extended_profiles(file):
    extended_files = {}
    config = get_file(file)
    extended_files[file] = config['metrics']
        for file_name in config['extends']:
            echo_info("config extends: " + config['extends'])
            extract_extended_profiles(file_name)
            return extended_files

    return extended_files










# {'MIB': 'CISCO-ENTITY-SENSOR-MIB', 'table': {'OID': '1.3.6.1.4.1.9.9.91.1.1.1', 'name': 'entSensorValueTable'}}
# {'MIB': 'CISCO-ENTITY-SENSOR-MIB', 'table': {'OID': '1.3.6.1.4.1.9.9.91.1.1.1', 'name': 'entSensorValueTable'}}
# {'MIB': 'CISCO-ENTITY-SENSOR-MIB', 'table': {'OID': '1.3.6.1.4.1.9.9.91.1.1.1', 'name': 'entSensorValueTable'}}
# {'MIB': 'PAN-COMMON-MIB', 'symbol': {'OID': '1.3.6.1.4.1.25461.2.1.2.3.1.0', 'name': 'panSessionUtilization'}}
# {'MIB': 'PAN-COMMON-MIB', 'symbol': {'OID': '1.3.6.1.4.1.25461.2.1.2.3.2.0', 'name': 'panSessionMax'}}
# {'MIB': 'PAN-COMMON-MIB', 'symbol': {'OID': '1.3.6.1.4.1.25461.2.1.2.3.3.0', 'name': 'panSessionActive'}}




def find_duplicates(profile):
    pass
# metrics need to be associated with their filenames
# Counter like object that can keep the metric-filename link




#collections.Counter(a).items() if count > 1]

def report_duplicates(profile):
    # duplicate metric oid and files it is defined in, line no?
    pass






