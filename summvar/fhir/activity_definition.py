"""
Abstraction for the FHIR Resource, ActivityDefinition

This acts as a container for the "Variables" associated with a single data table in a study dataset.
"""

from summvar import MissingIdentifier, BadIdentifier
from pprint import pformat
from copy import deepcopy
from summvar.fhir.observation_definition import ObservationDefinition

from rich.pretty import pprint
import pdb

import sys

from collections import namedtuple

# Just a simple way to deal with returns from the AD summary
# - unrecognized indicate which columns weren't matched to the header
# - unseen indicate which columns from the header weren't encountered
SummaryResult = namedtuple("SummaryResult", ["summaries", 
                                             "recognized", 
                                             "unrecognized", 
                                             "unseen",
                                             "enums"])

class ActivityDefinition:
    def __init__(self, client, resource=None, identifier=None, missing=set()):
        self.client = client
        self.resource_type = "ActivityDefinition"
        self.observation_definitions = []
        self.vocabulary = None
        self.missing_encoding = missing

        if resource is None:
            if identifier is None:
                raise MissingIdentifier(self.resource_type)

            resource = self.pull_details(identifier)

            if resource is None:
                raise BadIdentifier(self.resource_type, identifier)

        self.resource = resource
        self.name = resource['name']
        self.id = resource['id']
        self.identifier = resource['identifier'][0]
        self.url = None
        self.od_refs = []

        if 'observationResultRequirement' in resource:
            for od in resource['observationResultRequirement']:
                self.od_refs.append(od['reference'])

    @property
    def table_name(self):
        assert(len(self.resource['identifier']) == 1)
        return self.identifier['value']

    def reset(self):
        for od in self.observation_definition:
            od.reset()

    """There are a few things we need to track:
       - Which columns were successfully consumed
       - Which columns were not
       - various summary results
    """
    def summarize_rows(self, tabular_data, study_id, study_name, focus):
        columns_expected = set()
        columns_observed = set()
        summaries = []

        # We may not have loaded them yet, so this will force them to have been
        # loaded into memory
        obs_definitions = self.get_observation_definitions()
        enum_report = {}

        for row in tabular_data:
            for od in obs_definitions:
                colname = od.summarize_row(row)
                columns_expected.add(colname)
                if colname is not None:
                    columns_observed.add(colname)
        
        for od in obs_definitions:
            rpt = od.report_on_enumerations()
            if len(rpt) > 0:
                enum_report[od.code.code] = rpt
            summary = od.build_summary(self.client, study_id, study_name, focus=focus)
            if summary:
                if len(summary['component']) > 0:
                    summaries.append(summary)
                
        # Identify which columns didn't match
        # Is it safe to assume each row will have the same keys? It seems
        # reasonable, but I don't know if it's true
        unrecognized = set()

        if len(tabular_data) > 0:
            unrecognized = set(tabular_data[0].keys()) - columns_observed
        unseen_columns = columns_expected - columns_observed

        
        return SummaryResult(summaries=summaries, 
                             recognized=list(columns_observed),
                             unrecognized=list(unrecognized), 
                             unseen=list(unseen_columns),
                             enums=enum_report)

    def objectify(self, min=False, remote_host=None):
        obj = {}

        for prop in ['resourceType', 'name', 'title', 'identifier', 'status', 'topic']:
            obj[prop] = deepcopy(self.resource[prop])

        if not min:
            if remote_host is not None:
                obj['observationResultRequirement'] = []
                for od in self.observation_definitions:
                    obj['observationResultRequirement'].append({
                        "reference": od.remote_reference(remote_host)
                    })

            else:
                obj['observationResultRequirement'] = deepcopy(self.resource['observationResultRequirement'])

        return obj

    def load(self, remote_host):
        resource = self.objectify(remote_host=remote_host)
        identifier = f"{resource['identifier'][0]['system']}|{resource['identifier'][0]['value']}"
        response = remote_host.post(resource['resourceType'], resource, identifier=identifier)
        if response['status_code'] > 299:
            pprint(resource)
            resource
            pprint(response['response'])
            print(response['status_code'])
            sys.exit(1)
        response = response['response']

        remote_ref = f"{self.resource_type}/{response['id']}"
        #print(f"\ActivityDefinition: {remote_ref}")
        return response
    @property
    def count(self):
        return len(self.od_refs)

    @property
    def title(self):
        return self.resource['title']

    @property
    def reference(self):
        return f"{self.resource_type}/{self.id}"
    
    def get_vocabulary(self):
        if self.vocabulary is None:
            self.vocabulary = {}

            response = self.client.get(f"CodeSystem?url={self.url}")
            if response.success():
                if len(response.entries) > 0:
                    self.vocabulary[self.url] = response.entries[0]
        
            for od in self.get_observation_definitions():
                resources = od.get_vocabulary()

                if resources is not None:
                    self.vocabulary = {**resources, **self.vocabulary}
        return self.vocabulary

    def get_observation_definitions(self, force=False):
        """Realize the observation definitions based on the references from """
        """the AD body"""
        if force or len(self.observation_definitions) == 0:
            self.url = None
            for od in self.od_refs:
                response = self.client.get(od)

                if response.success():
                    entry = response.entries[0]

                    if 'resource' in entry:
                        entry = entry['resource']

                    if self.url is None:
                        if len(entry['code']['coding']) == 1:
                            if 'system' not in entry['code']['coding'][0]:
                                pprint(entry)
                                pdb.set_trace()
                            self.url = entry['code']['coding'][0]['system']
                    self.observation_definitions.append(ObservationDefinition(self.client, resource=entry, missing_encoding=self.missing_encoding))

        return self.observation_definitions

    def pull_details(self, identifier):
        """Pull the activity definition information from the FHIR server"""
        url = f"{self.resource_type}?identifier={identifier}"

        # We should be able to support pulling by reference
        if identifier.split("/")[0] == self.resource_type:
            url = identifier
        response = self.client.get(url)
        if response.success() and len(response.entries) > 0:
            entry_count = len(response.entries)
            if entry_count > 1:
                print(f"{self.resource_type}?identifier={identifier} returned {entry_count}. Ignoring all but the first")
            entry = response.entries[0]
            if 'resource' in entry:
                return entry['resource']
            return entry
        print(f"No responses were found for {self.resource_type}?identifier={identifier}")
        return None
