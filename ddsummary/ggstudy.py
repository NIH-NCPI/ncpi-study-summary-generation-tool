"""
Study specific details related to what we've found in firecloud as well as 
any details about the summaries themselves including issues encountered
"""

from ddsummary.ggtable import GoogleTable

class GStudy(GoogleTable):
    def __init__(self, title, key_source="JSON"):

        super().__init__(title, key_source)

    def load_cfg(self):
        # This is weird because the contents are not predefined, but, instead,
        # represent the workspaces that are identified as part of a given study
        # 
        self.workspaces = self.load_table('workspaces',
                                            keys=['namespace', 'name', 'table_name'],
                                            column_names=['study_id',
                                                'namespace',
                                                'name',
                                                'table_name',
                                                'dd_matches',
                                                'dd_missing',
                                                'unrecognized'])
        # After this, we'll have a detailed listing each dataset
        # table_name:dd_matches, table_name:dd_missing, table_name:unrecognized
        # where we list each variable that fits each of the categories