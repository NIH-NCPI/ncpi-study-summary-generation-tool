"""
Representation of the data-dictionary as loaded from FHIR. 
"""

from summvar.fhir.activity_definition import ActivityDefinition

import pdb 

class StudyDictionary:
    def __init__(self, client, tag):
        self.client = client
        self._metatag = tag.split("|")

        # ActivityDefinition resources
        self.activity_definitions = None      

    @property
    def tag_value(self):
        return self._metatag[-1]

    @property
    def tag_system(self):
        return self._metatag[0]

    @property
    def metatag(self):
        return "|".join(self._metatag)

    def summarize(self, study_id, namespace, wsname, data, focus):
        """"""
        alt_names = {"subject": "participant"}
        #pdb.set_trace()
        summary_results = {}
        for ad in self.activity_definitions:
            table_name = ad.table_name 

            if data is not None:
                if table_name in alt_names and table_name not in data:
                    table_name = alt_names[table_name]

                if table_name in data:
                    #pdb.set_trace()
                    summary_results[ad.table_name] = ad.summarize_rows(data[table_name], study_id, wsname, focus=focus)

                else:
                    print(f"{table_name} not present in our list of tables: {data.keys()}")
                    #pdb.set_trace()
            else:
                # We aren't summarizing new data here, only recalling the 
                # merged results from previous summaries for the given study
                summary_results[ad.table_name] = ad.summarize_rows([], study_id, None, focus=focus)
        return summary_results
    
    def load_activity_definitions(self, force=False, missing=set()):
        # We will take advantage of the meta.tag where we stashed the study ID

        #pdb.set_trace()
        if force or self.activity_definitions is None:
            self.activity_definitions = []
            response = self.client.get(f"ActivityDefinition?_tag={self.metatag}")
            #pdb.set_trace()
            if response.success():
                for entry in response.entries:
                    if 'resource' in entry:
                        entry = entry['resource']

                        ad = ActivityDefinition(self.client, resource=entry, missing=missing)
                        self.activity_definitions.append(ad)

        print(f"{len(self.activity_definitions)} Activity Definitions loaded for {self.metatag}")

        return self.activity_definitions
        
