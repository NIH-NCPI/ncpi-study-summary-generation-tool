"""
Configuration - We can keep some details about what we will run in a google
sheet with 2 tabs for input: 

    study - Each row would represent a single study (CMG or CCDG). One of the 
            columns would need to be the tag where that study's information is 
            found in FHIR
    workspaces - each row represents a single Terra workspace - One column must
            be the study "id"

    This same sheet might work for tracking details...maybe?
"""
from pathlib import Path
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from gspread.utils import rowcol_to_a1
import re
import json

from rich import print

import sqlite3 

import pdb

class GSheetConfig:
    sheet_url = "https://docs.google.com/spreadsheets/d/1xUh9FFQMeaiYHnVZooJ4RVgIqonMCOy_jLsbKBGiWQs"

    # For now, we'll hardcode the path to the key file 
    default_keyfile = Path.home() / "anvil-summary-a1b0931f10c6.json"

    worksheet_title = "AnVIL Summary Details"
    def __init__(self, key_source="JSON", url=None):
        self.url = url
        self.consortium_matchers = []
        if self.url is None:
            self.url = GSheetConfig.sheet_url 

        if key_source == "JSON":
            self.key_file = GSheetConfig.default_keyfile

            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]            
            self.creds = ServiceAccountCredentials.from_json_keyfile_name(self.key_file, scopes)
            self.google_doc = gspread.authorize(self.creds)
            self.doc = self.google_doc.open(GSheetConfig.worksheet_title)
        else:
            self.creds = gspread.service_account()
            self.doc = self.creds.open(GSheetConfig.worksheet_title)

        self.load_cfg()

    def reset_sheet(self, worksheet_name, data):
        """Delete existing worksheet data and replace it with whatever is in data"""
        worksheet = self.doc.worksheet(worksheet_name)
        row_count = len(data) 
        col_count = len(data['_header_'])

        data_chunk = [data['_header_']]
        print(f"Replacing [red]{worksheet_name}[/red] with [blue]{row_count}[/blue] rows: Columns {data_chunk[0]}")
        for k,v in data.items():
            if k != '_header_':
                data_chunk.append(v)

        worksheet.clear()
        worksheet.update(f'A1:{rowcol_to_a1(row_count, col_count)}', data_chunk)

    def save_cfg(self):
        """Just a cheap way to make sure the sheets are updated with any new information we have"""
        self.reset_sheet('consortium', self.consortium)
        self.reset_sheet('workspaces', self.workspaces)
        self.reset_sheet('tables', self.tables)
        self.reset_sheet('issues', self.issues)

    def load_table(self, title, keys=['consortium', 'workspace', 'table_name']):
        """Load data from the google doc table into local dictionary cache"""
        data = {}
        header = None
        for cns in self.doc.worksheet(title).get_all_values():
            if header is None:
                data['_header_'] = cns
                header = cns
            else:
                as_dict = dict(zip(header, cns))
                key_components = [as_dict[x] for x in keys]
                data["-".join(key_components)] = cns
        return data

    def load_cfg(self):
        self.consortium = self.load_table('consortium', keys=['name'])
        self.workspaces = self.load_table('workspaces', keys=['consortium', 'workspace'])
        self.tables = self.load_table('tables')
        self.issues = self.load_table('issues')

        # We will need to indicate which column(s) are required to recognize 
        # uniqueness across datasets. Questions remain, which columns do we
        # bind to these uniqueness constraints? Sex for participants, sure, 
        # but will there be columns in multiple participant tables that may be
        # suitable for counting every time it is encountered eve if this 
        # subject is present in more than one sub-study?
        self.key_columns = self.load_table('key_columns', ['consortium_name', 'table_name'])

        self.consortium_matchers = {}
        for cns, consortium in self.consortium.items():
            self.consortium_matchers[re.compile(consortium['ws_prefix'])] = consortium

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

