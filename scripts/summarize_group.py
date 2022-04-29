#!/usr/bin/env python

"""
Attempts to build Variable Summary observations for conditions that are associated
with members of groups. 

This is an example adhoc approach toward building out var summaries for data already
found inside fhir. 

It does require that groups exist and are populated with patients that may have one
or more Condition resource. For these vars, the total group membership will be the 
total N. We'll then summarize all conditions for each member. Missing will be inferred
based on the sum of all condition VerificationStatus codes

TODO: Think about some stuff
* We should be able to summarize over to a different server. 
    * Does my FhirHost even work for that or was there an assumption of one host?
    * There are a couple of pieces that these observations assume to exist and become referenced:
        * subject => group (which may not exist on destination server)
        * focus => Officially, this should be an observation definition...but do these make sense here?
        * value => This is probably safe to assume it's just the code associated with Condition...right?
"""

from os import getenv
import sys
from pathlib import Path
from yaml import safe_load
from ncpi_fhir_client.fhir_client import FhirClient
from argparse import ArgumentParser, FileType
from summvar.fhir.group import pull_groups, Group
from summvar.fhir import InitMetaTag,MetaTag,has_no_study
from summvar.summary.condition import summarize as summarize_conditions
from summvar.summary.patient import summarize as summarize_demo
from pprint import pformat
import pdb

def summarize_group(fhir_host, dest_host, group):
    group_ref = group.reference
    gdest = None
    ident = group.identifier
    gid = f"{ident['system']}|{ident['value']}"
    #pdb.set_trace()
    if fhir_host != dest_host:
        # First, we have to decide if the group exists on the remote, destination server
        try:
            gdest = Group(dest_host, identifier=gid)
            group_ref = gdest.reference
        except:
            # There is no valid group with that identifier
            tempgroup = group.objectify(min=True)
            #pdb.set_trace()
            response = dest_host.post('Group', tempgroup)
            if response['status_code'] == 201:
                resource = response['response']      
                gdest = Group(dest_host, resource = resource)     
                group_ref = gdest.reference 

    valid_summaries = 0
    invalid_summaries = 0
    hpo_summaries = summarize_conditions(fhir_host, group.name, group.p_refs, group_ref)
    demo_summaries = summarize_demo(fhir_host, group.name, group.p_refs, group_ref)
    #pdb.set_trace()
    for summary in hpo_summaries + demo_summaries:
        #pdb.set_trace()
        if gdest is not None:
            # Replace the subject with the correct group reference from the destination server
            summary['subject']['reference'] = gdest.reference
        identity = f"{summary['identifier'][0]['system']}|{summary['identifier'][0]['value']}"
        print(identity)

        response = dest_host.post('Observation', summary, identifier=identity)
        if response['status_code'] < 300:
            valid_summaries+=1
        else:
            print(pformat(response))
            pdb.set_trace()
            invalid_summaries += 1
    print(f"{ident['value']}: {valid_summaries} Added")
    if invalid_summaries > 0:
        print(f"{ident['value']}: {invalid_summaries} Failed")
    return gdest 
    
if __name__ == '__main__':
    hostsfile = Path(getenv("FHIRHOSTS", 'fhir_hosts'))
    config = safe_load(hostsfile.open("rt"))
    env_options = config.keys()
    parser = ArgumentParser()
    parser.add_argument("-s", 
                "--source-env", 
                choices=env_options, 
                default='dev', 
                help=f"Remote configuration to be used for querying data")
    parser.add_argument("-d", 
                "--dest-env", 
                choices=env_options, 
                help=f"Remote configuration to be used for writing data")
    parser.add_argument("-g", 
                "--group",
                type=str,
                default=[],
                action='append',
                help="Optional group to summarize over.")

    args = parser.parse_args()
    fhir_host = FhirClient(config[args.source_env])
    dest_host = fhir_host

    if args.dest_env:
        dest_host = FhirClient(config[args.dest_env])

    # If we didn't get one or more groups, identify available groups and let the user choose one
    if len(args.group) == 0:
        groups = pull_groups(fhir_host)

        all_groups = []
        for index in range(len(groups)):
            group = groups[index]
            print(f"{index + 1} - {group.name} with {group.count} patients")
            all_groups.append(group.reference)
        
        print("\nWhich group would you like to summarize (type index or all): ")
        index = input()
        if index.lower() == 'all':
            args.group = all_groups
        else:
            try:
                index = int(index)
            except:
                print("Hm. That doesn't make sense. Goodbye")
                sys.exit(1)
            
            args.group.append(groups[index-1].reference)
        
    for name in args.group:
        print(f"Working on the group, {name}")
        group = Group(fhir_host, identifier=name)
        #pdb.set_trace()

        summarize_group(fhir_host, dest_host, group)

                        
                

                




