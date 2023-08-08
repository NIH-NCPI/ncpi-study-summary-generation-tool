#!/usr/bin/env python

from collections import defaultdict

import firecloud.api as fapi

#from ddsummary.ggsummary import GSummary
from ddsummary.yamlcfg import SummaryConfig
from ddsummary.workspace import Workspace

import re
import sys

import pdb

from os import getenv
from ncpi_fhir_client.fhir_client import FhirClient
from summvar.data_dictionary import StudyDictionary
from pathlib import Path
from argparse import ArgumentParser, FileType
from yaml import safe_load
import json

from dbgap_study import DbGaPStudy, InvalidStudyID

from summvar.fhir import MetaTag, InitMetaTag

from rich import print
from rich.console import Console
from rich.table import Table
from rich.progress import track

from ddsummary.anvil_sources import get_workspaces
from summvar.fhir.activity_definition import ActivityDefinition
from summvar import system_prefix, system_url, study_id, create_dataset_study, create_study_group

from ncpi_fhir_client.ridcache import RIdCache


def get_id_name_from_workspace(workspace):
    idname = workspace.get("idName")
    if idname is None:
        idname = workspace.get("name")
    
    if idname is None:
        print(workspace)
        print("Unable to find idName or name")
        pdb.set_trace()
    
    return idname
"""
For the purposes of aggregate summaries, we can create copies of the AD 
resources to correspond to each of the different aggregate situations. So, if
we want to summarize over all workspaces for a given consortium as well as 
each individual workspace's data, we would have 2 sets of ADs with one of them
being reset in between workspace's assessment. 
"""

class DataDictionary:
    """We will be capturing data based on the underlying data dictionary.  """
    def __init__(self, client, wsconsortium):
        self.client = client
        self.tag = wsconsortium('tag')
        self.name = wsconsortium('name')
        self.ws_prefix = wsconsortium('ws_prefix')
        self.activity_definitions = []

    def load_activity_definitions(self):
        response = self.client.get(f"ActivityDefinition?_tag={self.tag}")
        if response.success():
            for entry in response.entries:
                if 'resource' in entry:
                    entry = entry['resource']
                    self.activity_definitions.append(ActivityDefinition(self.client, resource=entry))

    def summarize(self, namespace, ws_name, table_name, data):
        pass
        

def add_workspace(cfg, namespace, workspace, overwrite=False):
    """We won't overwrite what's already there unless overwrite is true"""

    table_schema = fapi.list_entity_types(namespace=namespace, workspace=workspace).json()
    for table_name in table_schema:
        table_data = fapi.get_entities(namespace, workspace, table_name)

        if type(table_data) is not dict:
            print(f"There is a problem with the entity: {namespace}/{workspace}")
            pdb.set_trace()

_varclean_x = re.compile("(\d+-|)(?P<colname>[\d\w]+)(-\d+|)")
def clean_varname(value):
    varname = _varclean_x.match(value)
    if varname is not None:
        return _varclean_x.match(value).group('colname').lower()

def prep_data(table_name, id_name, table_data):
    """The workspace header doesn't match the data-dictionary but we can help
       modify the headers to be more like what we expect. 
       
    """

    # Provide a lookup to be able to return the original header names for 
    # columns that must be reported as missing or invalid. 
    header_lookup = {}

    updated_data = []

    #pdb.set_trace()
    #if table_name == "aligned_dna_short_read_set":
    #    pdb.set_trace()

    for row in table_data:
        idname = clean_varname(id_name) + "_id"

        name = get_id_name_from_workspace(row)

        newrows = []
        newrow = {
            idname: name
        }
        newrows_as_list = defaultdict(list)
        try:
            was_complex = False
            for origcolname, value in row['attributes'].items():
                colname = clean_varname(origcolname) + "_id"

                #if colname == "aligned_dna_short_read_set":
                #    pdb.set_trace()
                # check for complex data
                if type(value) is dict:
                    if value.get('itemsType') == "EntityReference":
                        was_complex = True
                        #pdb.set_trace()
                        rows = []

                        for item in value['items']:
                            colid = clean_varname(item['entityType']) + '_id'
                            item_obj = {
                                idname: name,
                                f"{colid}": item['entityName'] 
                            }
                            newrows_as_list[colid].append(item['entityName'])
                            newrows.append(item_obj)
                else:
                    if colname is not None:
                        if was_complex and len(newrows) > 0:
                            if len(newrows_as_list) == 1:
                                # For now, we'll transform the singular column
                                # a pipe separated list. 
                                key = list(newrows_as_list.keys())[0]
                                value = "|".join(newrows_as_list[key])
                                # To avoid treating the newly minted rows as
                                # the real data, we'll clear them out. 
                                newrows = []
                            else:
                                print("OK. We probably shouldn't be here")
                                pdb.set_trace()
                                print(f"{colname}:{value}")
                        newrow[colname] = value
                        header_lookup[colname] = origcolname

            if len(newrows) > 0:
                for nr in newrows:
                    updated_data.append(nr)
                if len(newrow) > 1:
                    print("-----")
                    print(row)
                    print(f"----- {len(newrows)}")
                    print(newrows)
                    print(f"----- {len(newrow)}")
                    print(newrow)
                    print("\nWe shouldn't have both complex data and simple data....should we?")
                    pdb.set_trace()
            else:
                updated_data.append(newrow)
        except Exception as e:
            print(f"A Problem was encountered with ATTRIBUTES: {row}")
            print(e)

    return updated_data, header_lookup

_invalid_phs_ids = set(["Registration Pending", 
                        "TBD",
                        ""])
def filter_phs_id(value):
    if value is not None and value.strip() not in _invalid_phs_ids:
        return value

def exec(argv=None):
    # Identify the hosts we can choose from
    print("Summarize Workspaces")
    hostsfile = Path(getenv("FHIRHOSTS", 'fhir_hosts'))
    config = safe_load(hostsfile.open("rt"))
    env_options = config.keys()

    parser = ArgumentParser()
    parser.add_argument("--host", 
                choices=env_options, 
                required=True,
                help=f"FHIR server that contains meta-data resources and will "
                        "be the destination of the summary data")

    """
    parser.add_argument("--project",
                choices=["AnVIL Summary Details",
                         "GREGoR Summary Details"],
                default="AnVIL Summary Details",
                help="Google Sheet 'filename' configuration")
    """
    parser.add_argument("project",
                        nargs="+",
                        type=FileType('rt'),
                        help="Project YAML file")
    
    parser.add_argument("--missing",
                type=str,
                default="",
                help="Missing encoding as comma separated list of strings. "
                "No defaults are assumed.")
    
    parser.add_argument("-r",
                "--resource-log",
                help="Log resources and their status code/error message to a "
                    "JSON. If not provided, the log will be created inside "
                    "log/ based on the project name.")
    parser.add_argument("--report",
                help="Log correlations between each workspace and the data-"
                     "dictionary including missing tables, unexpected table "
                     "names and variables. ")

    args = parser.parse_args()

    # We'll send this to the client to 
    if args.resource_log is None:
        if len(args.project) == 1:
            args.resource_log = f"log/{args.project[0].name.lower().replace(' ', '_')}-{args.host}.json"
        else:
            print("You must provide --resource-log argument when summarizing "
                  "more than one configuration.")
            sys.exit(1)
    
    if args.report is None:
        if len(args.project) > 1:
            print("You must provide --report argument when summarizing more"
                  "than one configuration.")
            sys.exit(1)

        args.report = f"log/consensus-report-{args.project[0].name.lower()}.json"


    logpath = Path(args.resource_log)
    logpath.parent.mkdir(parents=True, exist_ok=True)

    #pdb.set_trace()
    cache_remote_ids = RIdCache()
    fhir_host = FhirClient(config[args.host], idcache=cache_remote_ids, cmdlog=args.resource_log)
    print(f"Connected to the host, {args.host}.")

    #pdb.set_trace()
    # gsumm = GSummary(title=args.project)
    gsumm = SummaryConfig()
    for prj in args.project:
        gsumm.add_consortium(prj)

    data_dictionaries = {    }

    # The data-dictionaries should be accessible at the "consortium" tab
    for cid, consortium in gsumm.consortium.items():
        data_dictionaries[cid] = StudyDictionary(fhir_host, consortium.tag)
        data_dictionaries[cid].load_activity_definitions(missing=consortium.missing)

    print("Connecting to fire cloud to download workspace data")
    # The file used for this data chunk should be a bit more up to date
    # Assuming names and workspace names are the same we should be able to use
    # this data for things like consortium and phsID
    base_workspaces = get_workspaces()
    workspaces = fapi.list_workspaces().json()
    print(f"{len(workspaces)} workspaces found.")

    table = Table(title=f"Parsing Workspace data:")
    table.add_column("Workspace Name", justify = "right", style="cyan")
    table.add_column("Namespace", style='purple')
    table.add_column("Tables", justify="left", style="yellow")



    # These are the aggregates for the DbGAP accession sub-studies
    study_summaries = {}
    study_problems = {}

    for wkspc in track(workspaces, f"Parsing workspaces"):
        #for wkspc in workspaces:
        ws = wkspc['workspace']
        wsname = ws['name']
        wsnamespace = ws['namespace']
        cns = gsumm.find_consortium(wsname)

        if cns is not None:
            #pdb.set_trace()
            system_prefix(cns.system_prefix)
            #pdb.set_trace()
            wkspace = Workspace(cns.name, wsnamespace, wsname, ws)

            #pdb.set_trace()
            phs_id = None
            if wsname in base_workspaces:
                # There is a lot of information in this file, so it probably 
                # will be more useful than just providing better matches for
                # the study's accession id. 
                #phs_id = filter_phs_id(base_workspaces[wsname].phsid)
                phs_id = base_workspaces[wsname].phsid
                if phs_id is not None:
                    wkspace.phs_id = phs_id
                    
            if filter_phs_id(wkspace.phs_id) and \
                            wkspace.phs_id not in study_summaries:
                
                try:
                    dbgstudy = DbGaPStudy(wkspace.phs_id)

                    study_group = dbgstudy.study_group()
                    sg_id = study_group['identifier'][0]

                    result = fhir_host.post("Group", 
                                            study_group,
                                            identifier=sg_id['value'],
                                            identifier_system=sg_id['system'],
                                            skip_insert_if_present=False)
                    if result['status_code'] >= 300:
                        print(result)
                        pdb.set_trace()

                    group_ref = f"Group/{result['response']['id']}"

                    
                    fhir_study = dbgstudy.for_fhir(cns.name)
                    fhir_study['enrollment'] = [
                        {
                            "reference": group_ref
                        }
                    ]
                    
                    result = fhir_host.post("ResearchStudy", 
                                            fhir_study, 
                                            identifier=fhir_study['identifier'][0]['value'],
                                            identifier_system=fhir_study['identifier'][0]['system'],
                                            skip_insert_if_present=True)
                    if result['status_code'] >= 300:
                        print(result)
                        pdb.set_trace()
                    study_identifier = fhir_study['identifier'][0]
                    study_summaries[wkspace.phs_id] = (cns.name, 
                                                    study_identifier['system'])
                    #pdb.set_trace()
                except InvalidStudyID as e:
                    print(f"Workspace: {wsname} references invalid study id: {wkspace.phs_id}")
                    wkspace.phs_id = None
                    #pdb.set_trace()
                except Exception as e:
                    print(e)
                    pdb.set_trace()
                    print("An unexpected exception was encountered")

            #pdb.set_trace()
            wkspace = gsumm.add_workspace(wkspace)
            cns.add_study(wkspace)

            #pdb.set_trace()
            study_group = create_study_group(
                            study=wkspace.phs_id,
                            dataset_name=wsname,
                            member_count=wkspace.subject_count
            )
            
            result = fhir_host.post("Group", 
                                    study_group,
                                    identifier=study_group['identifier'][0]['value'],
                                    identifier_system=study_group['identifier'][0]['system'],
                                    skip_insert_if_present=False)
            if result['status_code'] >= 300:
                print(result)
                pdb.set_trace()

            group_ref = f"Group/{result['response']['id']}"

            #research_study_id = study_id(cns['name'], phs_id, wsname)
            fhir_study = create_dataset_study(cns.name,
                                              study=wkspace.phs_id,
                                              dataset_name=wsname,
                                              title=None,
                                              web_url=None,
                                              description="TBD")
            fhir_study['enrollment'] = [
                {
                    "reference": group_ref
                }
            ]
            
            result = fhir_host.post("ResearchStudy", 
                                    fhir_study, 
                                    identifier=fhir_study['identifier'][0]['value'],
                                    identifier_system=fhir_study['identifier'][0]['system'],
                                    skip_insert_if_present=True)
            if result['status_code'] >= 300:
                print(fhir_study)
                print("  --------------------  ")
                print(result)
                pdb.set_trace()

            # Set the meta tag stuff to coincide with the study as we build out 
            # the various summary resources
            study_tag = fhir_study['meta']['tag'][0]
            InitMetaTag(study_tag['system'], study_tag['code'])
            #pdb.set_trace()
            study_fhir_id = result['response']['id']

            schema = fapi.list_entity_types(namespace=wsnamespace, workspace=wsname).json()
            #pdb.set_trace()

            # Schema gives us all of the tables, now we will pull the data for 
            # each of those tables and pass that along with the data-dictionary
            # reference to perform the summary
            table_data = {}
            header_lookup = {}
            for table_name in schema:
                # We have to fix those column names here, before we capture 
                # them in order to avoid putting workspace specific behavior
                # inside the more generic activity / observation classes. 
                # 
                # each "row" has an "attributes" property that points to the
                # individual row of data. Those rows are prefixed by numbers
                # probably some sort of sorting thing as well as a number 
                # at the end. The variable's name is like this 
                # [d]+-(varname)-[d]+
                # varname is currently mixed case. A quick scan suggests that
                # they don't include a mix of Snake Case and Humpback case, 
                # fortunately. 

               

                if type(schema[table_name]) is dict:
                    id_name = get_id_name_from_workspace(schema[table_name])

                    table_data[table_name], header_lookup[table_name] = prep_data(table_name, 
                                                id_name,
                                                fapi.get_entities(wsnamespace, 
                                                    wsname,
                                                    table_name).json())
                else:
                    print(f"Invalid schema format: {schema[table_name]} is {type(schema[table_name])}, not dict. ")
                    
            table_names = ",".join(table_data.keys())
            table.add_row(wsname, wsnamespace, table_names)
            #print(f"Workspace: {wsname}\t{wsnamespace}:{table_names}")
            summaries, unrecognized_tables = data_dictionaries[cns.name].summarize(wkspace.phs_id, wsnamespace, wsname, table_data, focus=f"ResearchStudy/{study_fhir_id}")
            study_problems[wsname] = {
                "recognized_tables": {},
                "unrecognized_tables": unrecognized_tables
            }
            #pdb.set_trace()
            for table_name in summaries:
                print(f"Loading {len(summaries[table_name].summaries)} for table, {table_name}. ")
                study_problems[wsname][table_name] = {}
                study_problems[wsname][table_name]["recognized_variables"] = summaries[table_name].recognized
                study_problems[wsname][table_name]['unrecognized_variables'] = summaries[table_name].unrecognized
                study_problems[wsname][table_name]['unseen_variables'] = summaries[table_name].unseen
                study_problems[wsname][table_name]['enumerations'] = summaries[table_name].enums
                for summary in summaries[table_name].summaries:
                    try:
                        
                        result = fhir_host.post("Observation", 
                                                summary,
                                                identifier=summary['identifier'][0]['value'],
                                                identifier_system=summary['identifier'][0]['system']
                                                )
                        if result['status_code'] >= 300:
                            print(result)
                            pdb.set_trace()
                    except Exception as e:
                        print(summary)
                        print("----------------------------------")
                        print(e)
                        print("----------------------------------")
                        pdb.set_trace()
                        print("Well, there was an exception")

    console = Console()
    console.print(table, justify="center")

    reportpath = Path(args.report)
    reportpath.parent.mkdir(parents=True, exist_ok=True)
    reportpath.write_text(json.dumps(study_problems, sort_keys=True, indent=2))
    print(f"Summary details written to log: {reportpath}")

    # Now, we should have complete summaries at the phsid level
    for phsid, (cns, study_system) in study_summaries.items():
        # Let's make sure each of our summary observations have the correct
        # tag associated with it
        InitMetaTag(study_system, phsid)
        #pdb.set_trace()
        summaries, unrecognized_tables = data_dictionaries[cns].summarize(phsid, None, None, None, focus=f"ResearchStudy/{phsid}")

        for table_name in summaries:
            print(f"Loading {len(summaries[table_name].summaries)} for table, {phsid}:{table_name}. ")

            for summary in summaries[table_name].summaries:
                
                result = fhir_host.post("Observation", 
                                        summary,                                        
                                        identifier=summary['identifier'][0]['value'],
                                        identifier_system=summary['identifier'][0]['system']
                                        )
                if result['status_code'] >= 300:
                    print(result)
                    pdb.set_trace()
    #gsumm.save_cfg()
if __name__ == '__main__':
    exec()

"""
workspaces = fapi.list_workspaces().json()
ws = workspaces[0]['workspace']
for k,v in ws.items():
    print(f"{k}:{v}")
pdb.set_trace()
"""