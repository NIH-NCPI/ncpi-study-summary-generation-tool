"""
Abstraction for FHIR research study
"""

from summvar import MissingIdentifier, BadIdentifier
from pprint import pformat
from copy import deepcopy

import pdb

class ResearchStudy:
    def __init__(self, client, resource=None, identifier=None):
        self.client = client
        self.resource_type = "ResearchStudy"

        if resource is None:
            if identifier is None:
                raise MissingIdentifier(self.resource_type)

            resource = self.pull_details(identifier)
            if resource is None:
                raise BadIdentifier(self.resource_type, identifier)

        self.resource = resource
        self.id = resource['id']
        self.identifier = resource['identifier'][0]
        self.g_refs = []

        if 'enrollment' in resource:
            for enrollment in resource['enrollment']:
                self.g_refs.append(enrollment['reference'])
    
    def objectify(self, min=False):
        obj = { }

        for prop in ['resourceType', 'title', 'identifier', 'status']:
            obj[prop] = deepcopy(self.resource[prop])
        
        if not min:
            obj['enrollment'] = deepcopy(self.resource['enrollment'])
        
        return obj

    @property
    def count(self):
        return len(self.g_refs)

    @property
    def title(self):
        return self.resource['title']

    @property
    def reference(self):
        return f"{self.resource_type}/{self.id}"

    def get_patients(self):
        patient_refs = []

        response = self.client.get(f"Patient?_has:ResearchSubject:individual:study={self.reference}")
        if response.success():
            for entry in response.entries:
                if 'resource' in entry:
                    entry = entry['resource']
                
                patient_refs.append(f"Patient/{entry['id']}")
        
        return patient_refs


    def pull_details(self, identifier):
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

def pull_studies(client, identifier = None, keep_empty_studies=False):
    """Build local representations for FHIR Research Study resources

    :param client: client connection to the FHIR server
    :type client: ncpi_fhir_client.fhir_client

    :param identifier: group identifier (optional)
    :type identifier: string

    :param keep_empty_studies: Indicates whether we ignore studies with no members
    :type keep_empty_studies: boolean

    If there is no identifier provided, the system will query
    all studies (with or without members based on params)
    """
    studies = []
    qry = ""
    if identifier is None:
        qry = "ResearchStudy"
    else:
        qry = f"ResearchStudy/identifier={identifier}"

    response = client.get(qry)
    if response.success():
        for entry in response.entries:
            study = ResearchStudy(client, resource=entry['resource'])
            if keep_empty_studies or study.count > 0:
                studies.append(study)
    else:
        print(f"There was a problem getting the group: {qry}")
    return studies
                