"""
Consortium details provided by the google sheet
"""

from ddsummary.ggtable import GoogleTable
from collections import defaultdict
import re

import pdb

class GSummary(GoogleTable):
    def __init__(self, 
                    title="AnVIL Summary Details",
                    key_source="JSON"):
        super().__init__(title, key_source)
        self.study_set = defaultdict(set)

    def save_cfg(self):
        """Just a cheap way to make sure the sheets are updated with any new information we have"""
        self.reset_sheet('consortium', self.consortium)
        self.reset_sheet('studies', self.studies)
        self.reset_sheet('workspaces', self.workspaces)
        self.reset_sheet('key_columns', self.key_columns)

    def load_cfg(self):
        self.consortium = self.load_table('consortium', 
                                        keys=['name'], 
                                        column_names=['name', 
                                                        'ws_prefix', 
                                                        'tag'])
        self.studies = self.load_table('studies',
                                        keys=['study_id'],
                                        column_names=['study_id',
                                                        'workspace_count',
                                                        'url'])
        # Each workspace should have a dbgap accession from which we can 
        # extract the base study phs number. 
        self.workspaces = self.load_table('workspaces', 
                                        keys=['consortium', 'workspace'],
                                        column_names = ['consortium',
                                                'workspace',
                                                'study_id',
                                                'dbgap_accession',
                                                'summary_log',
                                                'last_update',
                                                'summary_date'])

        # When trying to summarize at the "study" level, we'll need a way to 
        # identify data that may be common from multiple sub-study tables such
        # as demographics for the same person in multiple participant tables
        self.key_columns = self.load_table('key_columns',
                                        keys=['consortium',
                                                'table_name'],
                                        column_names=['consortium',
                                                'table_name',
                                                'key_columns'])

        # We will need to indicate which column(s) are required to recognize 
        # uniqueness across datasets. Questions remain, which columns do we
        # bind to these uniqueness constraints? Sex for participants, sure, 
        # but will there be columns in multiple participant tables that may be
        # suitable for counting every time it is encountered eve if this 
        # subject is present in more than one sub-study?
        #self.key_columns = self.load_table('key_columns', ['consortium', 
        #                                                    'table_name'])

        self.consortium_matchers = {}
        for cns, consortium in self.consortium.items():
            if cns != "_header_":
                print(consortium)
                self.consortium_matchers[re.compile(consortium['ws_prefix'])] = \
                                                        consortium

    def get_workspace(self, cns, namespace, wsname):
        return self.workspaces.get(f"{cns}-{namespace}/{wsname}")

    def add_workspace(self, wkspace):
        if wkspace.ws_key in self.workspaces:
            wkspace.merge(self.workspaces[wkspace.ws_key])
        else:
            self.workspaces[wkspace.ws_key] = wkspace.as_dict()
        #print(self.workspaces)
        print(f"Adding Workspace #{len(self.workspaces)}, {wkspace.name}")
        return wkspace

    def add_study(self, wkspace):
        if wkspace.phs_id is not None and wkspace.phs_id != "":
            if wkspace.phs_id not in self.studies:
                self.studies[wkspace.phs_id] = {
                    "study_id": wkspace.phs_id,
                    "workspace_count": 0,
                    "url": "??"
                }
            self.study_set[wkspace.phs_id].add(wkspace.ws_key)
            self.studies[wkspace.phs_id]['workspace_count'] = len(self.study_set[wkspace.phs_id])

    def find_consortium(self, wsname):
        """Return the first matching consortium dict encountered (or None)"""
        for x, consortium in self.consortium_matchers.items():
            if x.match(wsname):
                return consortium
        return None
        
    def in_consortium(self, wsname):
        """Return True/False if the workspace name matches one of the """
        """consortium prefixes"""
        for x in self.consortium_matchers:
            if x.match(wsname):
                return True
        return False

