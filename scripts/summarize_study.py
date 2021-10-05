#!/usr/bin/env python

"""
Attempts to build Variable Summary observations for conditions that are associated
with members of groups that are part of a specified study. 

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
from summvar.fhir.research_study import pull_studies, ResearchStudy
from summvar.fhir.group import Group
from summarize_group import summarize_group
from summvar.summary.condition import summarize as summarize_conditions
from pprint import pformat
import pdb

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
    parser.add_argument("--study",
                type=str,
                default=[],
                action='append',
                help="Optional study to summarize over.")

    args = parser.parse_args()
    fhir_host = FhirClient(config[args.source_env])
    dest_host = fhir_host

    if args.dest_env:
        dest_host = FhirClient(config[args.dest_env])

    # If we didn't get one or more groups, identify available groups and let the user choose one
    if len(args.study) == 0:
        studies = pull_studies(fhir_host)

        all_studies = []
        for index in range(len(studies)):
            study = studies[index]
            print(f"{index + 1} - {study.title} with {study.count} Groups")
            all_studies.append(study.reference)
        
        print("\nWhich group would you like to summarize (type index or all): ")
        index = input()
        if index.lower() == 'all':
            args.study = all_studies
        else:
            try:
                index = int(index)
            except:
                print("Hm. That doesn't make sense. Goodbye")
                sys.exit(1)
            
            args.study.append(studies[index-1].reference)
        
    for name in args.study:
        print(f"Working on the group, {name}")
        study = ResearchStudy(fhir_host, identifier=name)
        sdest = None
        #pdb.set_trace()

        group_refs = []
    
        # Now that we have a study, we should have 1 or more enrolled groups. For each of these,
        # we want to build out those summaries
        for group_ref in study.g_refs:
            group = Group(fhir_host, identifier=group_ref)
            remote_group = summarize_group(fhir_host, dest_host, group)
            if remote_group is not None:
                group_refs.append(remote_group.reference)

        if fhir_host != dest_host:
            # First, we have to decide if the group exists on the remote, destination server
            ident = study.identifier
            sid = f"{ident['system']}|{ident['value']}"
            try:
                sdest = ResearchStudy(dest_host, identifier=sid)
            except:
                # There is no valid group with that identifier
                temp = study.objectify(min=True)
                temp['enrollment'] = []

                for group_ref in group_refs:
                    temp['enrollment'].append({
                        "reference": f'{group_ref}'
                    })

                alt_titles = {
                    'BH_CMG': 'Baylor Hopkins Center for Mendelian Genomics (BH CMG)',
                    'UW_CMG': 'University of Washington Center for Mendelian Genomics (UW-CMG)',
                    'Y_CMG': 'Yale Center for Mendelian Genomics (Y CMG)'
                }

                if study.title in alt_titles:
                    temp['title'] = alt_titles[study.title]
                
                #pdb.set_trace()
                response = dest_host.post('ResearchStudy', temp)
                if response['status_code'] > 299:
                    print(pformat(response))
                print(response['status_code'])
                

                




