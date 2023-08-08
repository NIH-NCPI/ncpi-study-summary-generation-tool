"""
As great as using google docs seemed at the time, it was a bad idea. So, we'll
keep using the YAML file format for configuration that works well for Whistler.

I think the Whistler approach of one study per config works, except, for this
situation, we'll stick with one data-dictionary per study. If we want to 
explicitly enumerate each workspace, that is fine, but wildcards should be 
allowed as well. However, all matching workspaces should comply with the 
configuration's data dictionary.

"""

from pathlib import Path
import re

from yaml import safe_load
from collections import defaultdict
from rich import print

import pdb

class SummaryConfig:
    def __init__(self):

        # A consortium in this case represents one or more studies with a 
        # common data-dictionary
        self.consortium = {}

    def add_consortium(self, cfile):
        cfg = StudyConfig(cfile)

        self.consortium[cfg.name] = cfg

    def find_consortium(self, wsname):
        for cid, consortium in self.consortium.items():
            if consortium.in_consortium(wsname):
                return consortium
            
    def add_workspace(self, wkspace):
        cns = self.find_consortium(wkspace.ws_key)

        if cns is not None:
            return cns.add_workspace(wkspace)

class StudyConfig:
    def __init__(self, cfile):
        self.cfg = safe_load(cfile)

        self.name = self.cfg['name']
        self.ws_prefix = self.cfg['ws_prefix']
        self.system_prefix = self.cfg['system_prefix']
        self.tag = self.cfg['tag']
        self.meta_system, self.meta_tag = self.cfg['tag'].split("|")
        self.missing = self.cfg.get("missing")
        if self.missing is None:
            self.missing = set()
        else:
            self.missing = set(self.missing.split(","))

        self.cns_matcher = re.compile(self.ws_prefix)

        # workspace, study_id, dbgap_accession, summary_log, last_update, summary_date
        self.workspaces = {}

        # study_id, worspace_count, url
        self.studies = {}

        self.study_set = defaultdict(set)

    def find_consortium(self, wsname):
        if self.cns_matcher.search(wsname):
            return self.name
        
    def in_consortium(self, wsname):
        return self.cns_matcher.search(wsname) is not None
    
    def add_workspace(self, wkspace):
        #pdb.set_trace()
        if wkspace.ws_key in self.workspaces:
            self.workspaces[wkspace.ws_key].merge(wkspace)
        else:
            self.workspaces[wkspace.ws_key] = wkspace
        return self.workspaces[wkspace.ws_key]
    
    def add_study(self, wkspace):
        phsid = wkspace.phs_id
        if phsid is not None and phsid != "":
            if phsid not in self.studies:
                self.studies[phsid] = {
                    "study_id": phsid,
                    "workspace_count": 0,
                    "url": "??"
                }
            self.study_set[phsid].add(wkspace.ws_key)
            self.studies[phsid]['workspace_count'] = len(self.study_set[phsid])
