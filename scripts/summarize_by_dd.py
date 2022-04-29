#!/usr/bin/env python

"""
Attempts to assemble summary statistics for datasets which are using the 
FHIR data-dictionaries. 

"""

from os import getenv
import sys
from pathlib import Path
from yaml import safe_load
from ncpi_fhir_client.fhir_client import FhirClient
#from ncpi_fhir_plugin.common import constants
from argparse import ArgumentParser, FileType
from summvar.fhir.research_study import pull_studies, ResearchStudy
from summvar.fhir.group import Group
from summvar.fhir import InitMetaTag,MetaTag
from summvar.summary.condition import summarize as summarize_conditions
from time import sleep
import pdb

from rich.pretty import pprint
from rich.console import Console
from rich.live import Live
from rich.table import Table

def load_vocabulary(host, resource):
    retry_count = 5

    while retry_count > 0:
        identifier = f"{resource['identifier'][0]['system']}|{resource['identifier'][0]['value']}"
        response = host.post(resource['resourceType'], resource, identifier=identifier)
        if response['status_code'] > 299:
            retry_count -= 1
            sleep(2)
        else:
            retry_count = 0
    if response['status_code'] > 299:
        pprint(resource)
        pprint(response)
        pprint("We were unable to load the resource. ")
        sys.exit(1)
    return response

if __name__ == "__main__":

    # Identify the hosts we can choose from
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

    parser.add_argument("--no-condition", 
                action='store_true',
                help="When set, conditions will not be summarized")

    parser.add_argument("--study",
                type=str,
                action='append',
                help="Study to summarize over.")

    parser.add_argument("--full-dd", 
                action='store_true',
                help="When active, data-dictionary pieces will be copied to destination")

    args = parser.parse_args()
    
    fhir_host = FhirClient(config[args.source_env])
    dest_host = fhir_host

    if args.dest_env:
        dest_host = FhirClient(config[args.dest_env])

    target_studies = args.study
    # If we didn't get one or more groups, identify available groups and let the user choose one
    if len(target_studies) == 0:
        studies = pull_studies(fhir_host, keep_empty_studies=True)

        all_studies = []
        for index in range(len(studies)):
            study = studies[index]
            print(f"{index + 1} - {study.title} with {study.count} Groups")
            all_studies.append(study.reference)
        
        print("\nWhich study would you like to summarize (type index or all): ")
        index = input()
        if index.lower() == 'all':
            target_studies = all_studies
        else:
            try:
                index = int(index)
            except:
                print("Hm. That doesn't make sense. Goodbye")
                sys.exit(1)
            
            target_studies.append(studies[index-1].reference)

    # It is possible that some valuesets will be referenced by more than one 
    # variable and it doesn't make sense to load them over and over again. So,
    # we'll drop the url for each vocabulary we load in here and test for it 
    # prior to trying to load them
    saved_vocabs = set()



    console = Console()
    for name in target_studies:
        print(f"Working on the study, {name}")
        #pdb.set_trace()
        study = ResearchStudy(fhir_host, identifier=name)
        InitMetaTag(system=study.identifier['system'], code=study.identifier['value'])

        # Loading the study will also load the groups as well
        resource = study.load(dest_host)

        groups = study.get_groups()

        # This approach assumes the dd lives with the row-level data, which 
        # probably isn't always going to be true. We should probably move this
        # function over to the od file as a class method or global function
        activity_defs = study.get_activity_definitions()

        #pdb.set_trace()
        for ad in activity_defs:
            if fhir_host != dest_host:
                # Collect the vocabulary and load them into the remote host
                vocab = ad.get_vocabulary()

                #pdb.set_trace()
                code_systems_loaded = 0
                for url in vocab.keys():
                    resource = vocab[url]
                    if 'resource' in resource:
                        resource = resource['resource']

                    if 'resourceType' not in resource:
                        pprint(resource)
                        pdb.set_trace()
                    if resource['resourceType'] == 'CodeSystem':
                        del resource['id']
                        if resource['url'] not in saved_vocabs:
                            response = load_vocabulary(dest_host, resource)
                            code_systems_loaded += 1
                            saved_vocabs.add(resource['url'])

                # Give the code systems some time to merge into the database
                if code_systems_loaded > 0:
                    sleep(60)
                for url in vocab.keys():
                    resource = vocab[url]
                    if 'resource' in resource:
                        resource = resource['resource']
                        
                    if resource['resourceType'] == 'ValueSet':
                        del resource['id']
                        if resource['url'] not in saved_vocabs:
                            response = load_vocabulary(dest_host, resource)
                            saved_vocabs.add(resource['url'])

                if args.full_dd:
                    resource = ad.load(dest_host)

            #pdb.set_trace()
            ods = ad.get_observation_definitions()


            table = Table(title=f"Study Summary ({name}.{ad.name})", show_lines=2)
            table.add_column("Group", style="magenta")
            table.add_column("Variable", style="blue")
            table.add_column("Var Desc", style="red", ratio=2)
            table.add_column("Var Type", style="yellow")
            table.add_column("NonMiss", style="green" )
            table.add_column("Miss", style="bright_red")
            min_obs = None
            max_obs = None
            sum_counts = 0
            with Live(table, refresh_per_second=1):
                for od in ods:
                    for population in groups:
                        total_non_missing = 0
                        total_missing = 0
                        od.pull_observations(population)
                        varsummary = od.build_summary(dest_host)
                        if varsummary is not None:
                            total_non_missing = od.nonmissing_count
                            if min_obs is None or min_obs < od.nonmissing_count:
                                min_obs = od.nonmissing_count
                            if max_obs is None or max_obs > od.nonmissing_count:
                                max_obs = od.nonmissing_count
                            sum_counts += od.nonmissing_count
                            resource = dest_host.post(varsummary['resourceType'], 
                                            varsummary, 
                                            identifier=varsummary['identifier'][0]['value'], 
                                            identifier_system=varsummary['identifier'][0]['system'])
                            if not resource['status_code'] < 300:
                                pprint(varsummary)
                                pprint(resource)
                                sys.exit(1)

                            #pdb.set_trace()
                            table.add_row(population.name,
                                        od.identifier['value'],
                                        od.code.display,
                                        od.type_name,
                                        str(od.nonmissing_count),
                                        str(od.missing_count))
                        else:
                            total_missing += 1


        if not args.no_condition:
            print("Working on Conditions")
            for group in groups:
                table = Table(title=f"Condition Summary ({name}.{ad.name}.{group.name}) ", show_lines=2)
                table.add_column("Variable", style="blue")
                table.add_column("Var Desc", style="red", ratio=2)
                table.add_column("NonMiss", style="green" )
                table.add_column("Miss", style="bright_red")

                with Live(table, refresh_per_second=1):
                    valid_summaries = 0
                    invalid_summaries = 0
                    condition_summaries = summarize_conditions(fhir_host, name, group.p_refs, group.remote_reference(dest_host))
                    for summary in condition_summaries:
                        #pdb.set_trace()
                        table.add_row(summary['valueCodeableConcept']['coding'][0]['code'],
                                    summary['valueCodeableConcept']['coding'][0]['display'],
                                    str(summary['component'][0]['valueInteger']),
                                    str(summary['component'][1]['valueInteger'])
                                    )
                        identity = f"{summary['identifier'][0]['system']}|{summary['identifier'][0]['value']}"
                        response = dest_host.post(summary['resourceType'], summary, identifier=identity)

                        if response['status_code'] < 300:
                            valid_summaries+=1
                            #pdb.set_trace()
                            #print(f"\t\tSummary: {summary['resourceType']}/{response['response']['id']}")
                        else:
                            pprint(summary)
                            pprint(response)
                            pdb.set_trace()
                            invalid_summaries += 1

                print(f"{group.name}: {valid_summaries} Added")
                if invalid_summaries > 0:
                    print(f"{group.name}: {invalid_summaries} Failed")

