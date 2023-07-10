# This may have better information about the workspaces than
# the workspace meta data

#anvil_dash = "https://raw.githubusercontent.com/anvilproject/anvil-portal/main/plugins/utils/dashboard-source-anvil.tsv"

# This has been moved. At robert's suggestion, point to the last known version 
# until we better understand how to collect this data
anvil_dash ="https://raw.githubusercontent.com/anvilproject/anvil-portal/f42fcbbf91f78baef334b4af94a5fb676f5e1600/plugins/utils/dashboard-source-anvil.tsv"
import requests
from io import StringIO
import csv
from collections import defaultdict

import pdb 

invalid_phs = set(['Registration Pending', 'TBD', ""])

_workspaces = None

class AnvilDataset:
    def __init__(self, line):
        self.name = line['name']
        self.data = line

    @property
    def consortium(self):
        return self.data['consortium']
    
    @property
    def phsid(self):
        try:
            phs = self.data['phsId'].strip()
        except:
            print("No PHS Id in this one")
            pdb.set_trace()

        if phs not in invalid_phs:
            return phs

        return None

def get_workspaces(url=anvil_dash):
    global _workspaces
    if _workspaces is None:
        _workspaces = {}

        response = requests.get(url)
        if response.status_code < 300:
            with StringIO(response.text) as fd:
                rd = csv.DictReader(fd, delimiter="\t", quotechar='"')
                for row in rd:
                    ds = AnvilDataset(row)
                    _workspaces[ds.name] = ds
        else:
            print(f"{url} : {response.text}")
            print("Unable to populated the workspaces with additional info")
    
    return _workspaces

