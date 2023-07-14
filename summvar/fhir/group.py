"""
 Abstraction for FHIR group resources
"""

from pprint import pformat
from copy import deepcopy
import sys
from rich import pretty

from summvar import MissingIdentifier, BadIdentifier
from summvar.fhir import MetaTag
import pdb

pretty.install()

class Group:
    def __init__(self, client, resource=None, identifier=None):
        self.client = client
        self.resource_type = "Group"
        self.remote_ref = None

        if resource is None:
            if identifier is None:
                raise MissingIdentifier(self.resource_type)

            resource = self.pull_details(identifier)
            if resource is None:
                raise BadIdentifier(self.resource_type, identifier)

        self.resource = resource
        self.identifier = resource['identifier'][0]
        self.p_refs = []

        # We'll keep only the identifiers in a set for fast lookup
        self.p_identifiers = None

        self.id = None
        if 'id' in resource:
            self.id = resource['id']
        if 'member' in resource:
            for entity in resource['member']:
                self.p_refs.append(entity['entity']['reference'])

    def is_member(self, patient_ref):
        if self.p_identifiers is None:
            self.p_identifiers = set()

            for p in self.p_refs:
                self.p_identifiers.add(p.split("/")[-1])

        pid = patient_ref = patient_ref.split("/")[-1]

        return pid in self.p_identifiers

    def load(self, remote_host):
        resource = self.objectify(min=True)
        response = remote_host.post(resource['resourceType'], resource, identifier=self.dest_identifier)
        if response['status_code'] > 299:
            print(resource)
            resource
            print(response['status_code'])
            print(response['response'])
            sys.exit(1)
        response = response['response']

        self.remote_ref = f"{self.resource_type}/{response['id']}"
        return response

    def remote_reference(self, remote_host):
        #pdb.set_trace()
        if self.remote_ref is None:
            resource = self.load(remote_host)
            self.remote_ref = f"{self.resource_type}/{resource['id']}"
        
        return self.remote_ref
    
    def objectify(self, min=False, source=False):
        obj = { 
            'meta': {
                'profile': [
                    "https://ncpi-fhir.github.io/ncpi-fhir-study-summary-ig/StructureDefinition/study-summary-group"
                ],
                'tag': MetaTag()
            }
        }

        idnt = self.build_dest_identifier()
        if source:
            idnt = self.resource['identifier']
        obj['identifier'] = idnt
        obj['actual'] = True

        for prop in ['resourceType', 'name', 'type']:
            if prop in self.resource:
                obj[prop] = deepcopy(self.resource[prop])
        if 'member' in self.resource:
            obj['quantity'] = len(self.resource['member'])

            if not min:
                obj['member'] = deepcopy(self.resource['member'])

        return obj

    @property
    def count(self):
        return len(self.p_refs)

    @property
    def name(self):
        if 'name' in self.resource:
            return self.resource['name']
        else:
            return self.resource['identifier'][0]['value']

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
        if self.id is None:
            pdb.set_trace()
        return f"{self.resource_type}/{self.id}"

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
        print(f"No responses were found for {self.resource_type}/identifier={identifier}")
        return None
    
def pull_groups(client, identifier = None, keep_empty_groups=False):
    """Build local representations for FHIR Group resources

    :param client: client connection to the FHIR server
    :type client: ncpi_fhir_client.fhir_client

    :param identifier: group identifier (optional)
    :type identifier: string

    :param keep_empty_groups: Indicates whether we ignore groups with no members
    :type keep_empty_groups: boolean

    If there is no identifier provided, the system will query
    all groups (with or without members based on params)
    """
    groups = []
    qry = ""
    if identifier is None:
        qry = "Group"
    else:
        qry = f"Group/identifier={identifier}"

    response = client.get(qry)
    if response.success():
        for entry in response.entries:
            group = Group(client, resource=entry['resource'])
            if keep_empty_groups or group.count > 0:
                groups.append(group)
    else:
        print(pformat(response))
        print(f"There was a problem getting the group: {qry}")
    return groups
                