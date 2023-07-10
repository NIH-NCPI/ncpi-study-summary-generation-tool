#!/usr/bin/env python

"""
Provide a simple script for pulling data from firecloud API and write it out as JSON file
"""

import firecloud.api as fapi

from os import getenv

from pathlib import Path
from argparse import ArgumentParser, FileType
from yaml import safe_load

from rich import print
import json
import re 

import pdb

has_extension = re.compile("\.json$", re.I)

if __name__ == '__main__':

    parser = ArgumentParser("Pull Workspace Data - Pulls data from the firecloud API into JSON file suitable for debugging our summary scripts")
    parser.add_argument("workspaces",
                        type=str, 
                        nargs="+",
                        help="A Workspace to be pulled from firecloud")

    parser.add_argument("-o",
                        "--out",
                        type=str,
                        default=None,
                        help="Filename to write the results to (defaults to the first workspace name in output/)")
    
    args = parser.parse_args()

    workspaces = fapi.list_workspaces().json()

    workspace_resources = {}

    print(f"Searching for workspaces: {args.workspaces}")
    
    for workspace in workspaces:
        workspace_name = workspace['workspace']['name']
        ws_namespace = workspace['workspace']['namespace']
        if workspace_name in args.workspaces:
            print(workspace_name)

            table_schema = fapi.list_entity_types(namespace=ws_namespace, 
                                                  workspace=workspace_name).json()
            ws_resources = {
                "workspace" : workspace,
                "schema": table_schema,
                "tables": {}
            }

            for table_name in table_schema:
                table_data = fapi.get_entities(ws_namespace, workspace_name, table_name).json()
                #print(table_data)
                ws_resources["tables"][table_name] = table_data
            
            workspace_resources[workspace_name] = ws_resources

    if len(workspace_resources) > 0:
        filename = args.out
        if args.out is None:
            filename = "output/" + "-".join(args.workspaces)

        if not has_extension.match(filename):
            filename = filename + ".json"
            
        filename = Path(filename)
        print(f"Writing {len(workspace_resources)} to {filename}")
        if not filename.parent.exists:
            filename.parent.mkdir(parents=True, exist_ok=True)

        filename.write_text(json.dumps(workspace_resources, sort_keys=True, indent=2))


