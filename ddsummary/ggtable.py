"""
Base class for googlesheet adaptor classes
"""
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from gspread.utils import rowcol_to_a1
from pathlib import Path

from rich import print
import pdb

class GoogleTable:
    # For now, we'll hardcode the path to the key file 
    default_keyfile = Path.home() / "anvil-summary-a1b0931f10c6.json"
    def __init__(self, title, key_source="JSON"):
        self.title = title
        if key_source == "JSON":
            print(f"Using the keyfile: {GoogleTable.default_keyfile}")
            self.key_file = GoogleTable.default_keyfile

            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]            
            self.creds = ServiceAccountCredentials.from_json_keyfile_name(self.key_file, scopes)
            self.google_doc = gspread.authorize(self.creds)
            try:
                print(f"Opening the document: {title}")
                # If the doc exists, let's open it
                self.doc = self.google_doc.open(title)
            except:
                print(f"Attempting to create a document: {title}")
                self.doc = self.google_doc.create(title)
                # https://docs.gspread.org/en/latest/api/models/spreadsheet.html#gspread.spreadsheet.Spreadsheet.share
                self.doc.share('eric.s.torstenson@vumc.org', perm_type='user', role='owner')
        else:
            self.creds = gspread.service_account()
            self.doc = self.creds.open(title)
            
        self.url = self.doc.url

        self.load_cfg()

    def load_table(self, 
                    title, 
                    keys=['consortium', 'workspace', 'table_name'],
                    column_names=None):
        """Load data from the google doc table into local dictionary cache"""
        data = {}
        header = None
        
        try:
            ws = self.doc.worksheet(title)
            for cns in self.doc.worksheet(title).get_all_values():
                if header is None:
                    header = cns

                    if column_names is not None:
                        remaining_cols = set(column_names) - set(header)
                        if len(remaining_cols) > 0:
                            header += list(remaining_cols)
        
                        data['_header_'] = header

                else:
                    as_dict = dict(zip(header, cns))
                    key_components = [as_dict[x] for x in keys]
                    data["-".join(key_components)] = as_dict
                    
        except gspread.exceptions.WorksheetNotFound:
            assert(column_names is not None)
            ws = self.doc.add_worksheet(title=title, rows=1, cols=len(column_names))
            ws.append_row(column_names)

            data['_header_'] = header
        return data

    def reset_sheet(self, worksheet_name, data):
        """Delete existing worksheet data and replace it with whatever is in data"""
        print(f"Worksheet: {worksheet_name}")
        worksheet = self.doc.worksheet(worksheet_name)
        row_count = len(data) 
        col_count = len(data['_header_'])

        data_chunk = [data['_header_']]
        print(f"Replacing [red]{worksheet_name}[/red] with [blue]{row_count}[/blue] rows: Columns {data_chunk[0]}")
        for k,v in data.items():
            # header has already been written to the data_chunk
            if k != '_header_':
                try:
                    row = []
                    for col in data_chunk[0]:
                        if col in v:
                            row.append(v[col])
                        else:
                            row.append("")
                    data_chunk.append(row)
                except:
                    print(data_chunk[0])
                    print(v)
                    pdb.set_trace()


        #pdb.set_trace()
        worksheet.clear()
        worksheet.update(f'A1:{rowcol_to_a1(row_count, col_count)}', data_chunk)

    def load_cfg(self):
        # This should be handled at the child class since it will be specific 
        # to whatever that sheet is intended to capture
        assert(False)

    def save_cfg(self):
        assert(False)
