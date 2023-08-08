"""
Basic encapsulation of workspace details with ability to capture details about
tables summarize, problem variables, etc. This should be able to be produced
from the google sheet doc as well as save back to the sheets when ready
"""
from rich import print
import re

import pdb

anvil_dash = "https://raw.githubusercontent.com/anvilproject/anvil-portal/main/plugins/utils/dashboard-source-anvil.tsv"

dbgapx = re.compile(":[\s]*(?P<phs>phs[\d]+)", re.I)

def choose(first_choice, second_choice):
    """Returns first_choice over second_choice or empty string"""
    if first_choice is not None and first_choice.strip() != "":
        return first_choice
    
    if second_choice is None:
        return ""
    return second_choice

class Workspace:
    def __init__(self, consortium, namespace, name, wsdetail=None, ggsource=None):
        self.consortium = consortium
        self.namespace = namespace 
        self.name = name
        self.subject_count = 0

        self.fields_summarized = []
        
        if ggsource is not None:
            """ggsource is what comes from the google sheet if it already exists"""
            self.phs_id = ggsource.get('study_id')
            self.study_accession = ggsource.get('dbgap_accession')
            self.summary_log = ggsource.get("summary_log")
            self.last_update = ggsource.get("last_update")
            self.summary_date = ggsource.get("summary_date")
        
        else:
            """wsdetail is the workspace response from firecloud"""
            self.phs_id = self.parse_phs(wsdetail)
            self.study_accession = wsdetail['attributes'].get('study_accession')
            self.summary_log = ""
            self.last_update = wsdetail['lastModified']
            self.summary_date = ""
            self.subject_count = self.get_subject_count(wsdetail)

    def merge(self, other):
        self.consortium = choose(self.consortium, other['consortium'])
        self.phs_id = choose(self.phs_id, other.get('study_id'))
        self.study_accession = choose(other.get("dbgap_accession"), self.study_accession)
        self.summary_log = choose(other.get("summary_log"), self.summary_log)
        self.last_update = choose(self.last_update, other.get("last_update"))
        self.summary_date = choose(other.get("summary_date"), self.summary_date)
        other_count = self.get_subject_count(other)

        if other_count:
            self.subject_count += self.get_subject_count(other)

    def get_subject_count(self, wsdetail):
        if 'attributes' in wsdetail:
            if 'library:numSubjects' in wsdetail['attributes']:
                try:
                    return int(wsdetail['attributes'].get('library:numSubjects'))
                except:
                    print(f"Invalid value for {self.name}'s numSubjects: '{wsdetail['attributes'].get('library:numSubjects')}'")
                    #pdb.set_trace()
                    return 0


    @property
    def workspace(self):
        return f"{self.namespace}/{self.name}"

    @property
    def ws_key(self):
        return f"{self.consortium}-{self.workspace}"

    def as_dict(self):
        obj = {
            "consortium": self.consortium,
            "workspace": self.workspace, 
            "summary_log": self.summary_log, 
            "last_update": self.last_update,
            "summary_date": self.summary_date
        }
        if self.phs_id:
            obj['study_id'] = self.phs_id
        if self.study_accession:
            obj['dbgap_accession'] = self.study_accession

        return obj

    def parse_phs(self, data):
        attribs = data['attributes']
        
        phs = attribs.get('study_phs')
        if phs is None:
            try:
                phs = attribs.get("study_accession").split(".")[0]
            except:
                pass

        if phs is None:
            x = dbgapx.search(str(data))

            if x:
                phs = x['phs']

        return phs