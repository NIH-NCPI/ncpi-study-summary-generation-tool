# Basic wrapper around a basic json object for dumping resources and responses
# from the FHIR server

import pdb

from rich import print
from pathlib import Path

class ResourceLogger:
    def __init__(self, filename, project, target_host):
        self.filename = Path(filename)
        # create directory if it doesn't currently exist
        filedir = self.filename.parent
        filedir.mkdir(parents=True, exist_ok=True)

        self.project = project
        self.target_host = target_host

        # Write json objects to a temporary file in case the application
        # dies before the final log is created
        self.temp_filepath = Path(f"{filename}.tmp")
        self.temp_log = self.temp_filepath.open(mode='wt')
        self.temp_log.write(f"""project: {project}\n""")
        self.temp_log.write(f"""destionation: {target_host}""")

        self.data = []

    def log_resource(self, response):
        print(response)
        pdb.set_trace()
        self.data.append(response)