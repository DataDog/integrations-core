from collections import Counter
from queue import Queue

import click
import yaml

from ....constants import get_root
from ...console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success
from .....fs import file_exists


@click.command("check-duplicates", short_help="Check SNMP profiles for duplicate metrics", context_settings=CONTEXT_SETTINGS)
@click.option('-f', '--file', help="Path to a profile file to validate")
# @click.option('-d', '--directory', help="Path to a directory of profiles to validate")
@click.option('-v', '--verbose', help="Increase verbosity of error messages", is_flag=True)

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

class Profile:
    def __init__(self):
        self.extends = set()
        self.metrics = []
        self.counter = {}
        self.oids = []
        self.path = ""
        self.has_duplicates = False


    def __repr__(self):
        return self.path

    def extract_extended_files(self, file):
        to_visit = Queue()
        self.seen = set()
        to_visit.put(file)
        while not to_visit.empty():
            file = to_visit.get()
            if file not in self.seen:
                config = get_file(file)
                try:
                    for extended_profile in config['extends']:
                        to_visit.put(extended_profile)
                except KeyError:
                    pass
                self.seen.add(file)
        self.extends = self.seen

    def extract_oids(self, metrics_blob):
        self.oids_list = []
        for list_element in metrics_blob:
            if "symbol" in list_element.keys():
                oids = extract_oids_from_metric(list_element)
                self.oids_list = self.oids_list + oids
            if "symbols" in list_element.keys():
                oids = extract_oids_from_table(list_element)
                self.oids_list = self.oids_list + oids
            if "OID" in list_element:
                oids = extract_oids_from_legacy(list_element)
                self.oids_list = self.oids_list + oids
        return(self.oids_list)

    def find_duplicates(self, oids):
        for oid in oids.values():
            counter = Counter(oid) #oid:count

        duplicates = {k:v for (k,v) in counter.items() if v > 1}

        if duplicates:
            #extract filename as string
            # duplicate oids are an error
            echo_failure("Duplicate value found in " + str(oids.keys()) + " at OIDS:")
            for el in duplicates:
                echo_failure(str(el))

            #where files are imported
            #class for oids - oid and profile
            # reverse lookup? find where oid is defined - key is oid and value is list of files

def create_profile(file):
    profile = Profile()
    profile.path = file
    profile.extract_extended_files(file)
    for extended_profile in profile.extends:
        config = get_file(file)
        profile.metrics.append(config['metrics'])
    for blob in profile.metrics:
        profile.oids = profile.extract_oids(blob)
    profile.counter = construct_oid_counter(profile)
    return profile



def construct_oid_counter(profile):
    #{oid: [path, path]}
    counter = {}
    for oid in profile.oids:
        for path in profile.extends:
            if oid in counter:
                counter[oid].append(path)
            counter[oid] = [path]
    return counter




def extract_oids_from_metric(metric_dict):
    oids_list = []
    oids_list.append(metric_dict['symbol']['OID'])
    return oids_list


def extract_oids_from_table(metric_dict): # not sure about this one?
    oids_list = []
    for item in metric_dict['symbols']:
        oids_list.append(item['OID'])
    return(oids_list)

def extract_oids_from_legacy(metric_dict):
    oids_list = []
    oids_list.append(metric_dict['OID'])
    return oids_list


def get_file(file):
    with open(file) as f:
        return yaml.safe_load(f)
















