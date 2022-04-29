"""
Abstraction for FHIR research study
"""

from summvar import MissingIdentifier, BadIdentifier
from pprint import pformat
from copy import deepcopy
from summvar.fhir.activity_definition import ActivityDefinition
from summvar.fhir.group import Group
from summvar.fhir import MetaTag

import pdb

class ResearchStudy:
    def __init__(self, client, resource=None, identifier=None):
        self.client = client
        self.resource_type = "ResearchStudy"
        self.remote_ref = None

        if resource is None:
            if identifier is None:
                raise MissingIdentifier(self.resource_type)

            resource = self.pull_details(identifier)
            if resource is None:
                raise BadIdentifier(self.resource_type, identifier)

        self.resource = resource
        self.id = resource['id']
        self.identifier = resource['identifier'][0]
        
        self.groups = []
        self.g_refs = []

        self.activity_definitions = []

        if 'enrollment' in resource:
            for enrollment in resource['enrollment']:
                self.g_refs.append(enrollment['reference'])

    def remote_reference(self, remote_host):
        if self.remote_ref is None:
            resource = self.load(remote_host)
            self.remote_ref = f"{self.resource_type}/{resource['id']}"
        
        return self.remote_ref

    def load(self, remote_host):
        resource = self.objectify(remote_host=remote_host)
        response = remote_host.post(resource['resourceType'], resource, identifier=self.dest_identifier)
        if response['status_code'] > 299:
            print(resource)
            print(response['status_code'])
            print(response['response'])
            sys.exit(1)
        response = response['response']
        self.remote_ref = f"{self.resource_type}/{response['id']}"
        print(f"Study: {self.remote_ref}")
        return resource

    def get_groups(self):
        if len(self.groups) == 0:
            for gref in self.g_refs:
                group = Group(self.client, identifier=gref)
                self.groups.append(group)

        return self.groups
    
    def objectify(self, min=False, remote_host=None):
        groups = self.get_groups()
        obj = { 
            'meta': {
                'profile': [
                    "https://ncpi-fhir.github.io/ncpi-fhir-study-summary-ig/StructureDefinition/summary-research-study"
                ],
                'tag': MetaTag()
            }
        }

        idnt = self.build_dest_identifier()
        if remote_host is None:
            idnt = self.resource['identifier']

        obj['identifier'] = idnt
        for prop in ['resourceType', 'title', 'status']:
            obj[prop] = deepcopy(self.resource[prop])
        
        #pdb.set_trace()
        if not min:
            if remote_host:
                enrollment = []

                for group in self.groups:
                    enrollment.append({"reference" : group.remote_reference(remote_host)})
            else:
                enrollment = deepcopy(self.resource['enrollment'])

            if len(enrollment) > 0:
                print(enrollment)
                obj['enrollment'] = enrollment
        
        return obj

    @property
    def count(self):
        return len(self.g_refs)

    @property
    def title(self):
        return self.resource['title']


    @property
    def source_identifier(self):
        idnt = self.resource['identifier'][0]
        return f"{idnt['system']}|{idnt['value']}"

    def build_dest_identifier(self):
        idnt = deepcopy(self.resource['identifier'])
        idnt[0]['system'] += '-summary'
        idnt[0]['value']+= '-summary'
        return idnt

    @property
    def dest_identifier(self):
        idnt = self.build_dest_identifier()[0]
        return f"{idnt['system']}|{idnt['value']}"


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

    def get_activity_definitions(self, force=False):
        # We will take advantage of the meta.tag where we stashed the study ID

        if len(self.activity_definitions) == 0 or force:
            identifier = f"{self.identifier['system']}|{self.identifier['value']}"

            response = self.client.get(f"ActivityDefinition?_tag={identifier}")
            if response.success():
                for entry in response.entries:
                    if 'resource' in entry:
                        entry = entry['resource']

                        ad = ActivityDefinition(self.client, resource=entry)
                        self.activity_definitions.append(ad)
        return self.activity_definitions

    def pull_details(self, identifier):
        url = f"{self.resource_type}?identifier={identifier}"

        # We should be able to support pulling by reference
        print(identifier)
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
                