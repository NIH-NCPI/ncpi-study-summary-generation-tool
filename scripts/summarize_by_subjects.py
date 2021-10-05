#!/usr/bin/env python

"""
Attempts to build Variable Summary observations for conditions that are associated
with members of studies by way of ResearchSubject. This is necessary for data that
hasn't been loaded using ResearchStudy.enrollment and consent level groups. 

This is an example adhoc approach toward building out var summaries for data already
found inside fhir. 

It does require that ResearchSubjects exist to link patients to the study. We'll 
fabricate a single group to represent the subject of the summary observations.

"""

from os import getenv
import sys
from pathlib import Path
from yaml import safe_load
from ncpi_fhir_client.fhir_client import FhirClient
from ncpi_fhir_plugin.common import constants
from argparse import ArgumentParser, FileType
from summvar.fhir.research_study import pull_studies, ResearchStudy
from summvar.fhir.group import Group
from summarize_group import summarize_group
from summvar.summary.condition import summarize as summarize_conditions
from pprint import pformat
import pdb


varsum_code = {
    'coding': [{
        'system': 'https://ncpi-fhir.github.io/ncpi-code-systems',
        'code': 'Summary',
        'display': "Variable Summary"
    }],
    'text': "Variable Summary"
}

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
        studies = pull_studies(fhir_host, keep_empty_studies=True)

        all_studies = []
        for index in range(len(studies)):
            study = studies[index]
            print(f"{index + 1} - {study.title} with {study.count} Groups")
            all_studies.append(study.reference)
        
        print("\nWhich study would you like to summarize (type index or all): ")
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
        print(f"Working on the study, {name}")
        #pdb.set_trace()
        study = ResearchStudy(fhir_host, identifier=name)
        patient_refs = study.get_patients()

        group_name = study.title
        if len(group_name) > 50:
            group_name = study.identifier['value']
        
        try:
            group_identifier = f"{constants.NCPI_DOMAIN}/variable-definition|{group_name.replace(' ', '-')}"
            group = Group(dest_host, identifier=group_identifier)
        except:
            tempgroup = {
            "resourceType": "Group",
            'identifier': [{
                    'system': f'{constants.NCPI_DOMAIN}/variable-definition',
                    'value': group_name.replace(" ", "-") 
                },
                study.identifier
            ],
            'type': 'person',
            'actual': True,
            'name': group_name
        }
            response = dest_host.post('Group', tempgroup)
            if response['status_code'] == 201:
                resource = response['response']
                group = Group(dest_host, resource=resource)
            
        if len(group.p_refs) == 0:       
            #pdb.set_trace()
            group.p_refs = patient_refs

        remote_group = summarize_group(fhir_host, dest_host, group)
       
        # If the destination host does have the study and it does have enrollment that differs
        # from our one group, then we are not going to continue.
        ident = study.identifier
        sid = f"{ident['system']}|{ident['value']}"
        enrollments = [{
                'reference': remote_group.reference
            }]
        try:
            sdest = ResearchStudy(dest_host, identifier=sid)
            if 'enrollment' in sdest.resource:
                assert(sdest.resource['enrollment'] == enrollments)
        except:
            temp = study.objectify(min=True)
            temp['enrollment'] = enrollments

            #pdb.set_trace()
            response = dest_host.post('ResearchStudy', temp)
            print(response['status_code'])
                

                




