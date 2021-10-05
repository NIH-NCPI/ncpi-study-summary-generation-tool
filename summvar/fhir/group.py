"""
 Abstraction for FHIR group resources
"""

from pprint import pformat
from copy import deepcopy

from summvar import MissingIdentifier, BadIdentifier
import pdb
class Group:
    def __init__(self, client, resource=None, identifier=None):
        self.client = client
        self.resource_type = "Group"

        if resource is None:
            if identifier is None:
                raise MissingIdentifier(self.resource_type)

            resource = self.pull_details(identifier)
            if resource is None:
                raise BadIdentifier(self.resource_type, identifier)

        self.resource = resource
        self.identifier = resource['identifier'][0]
        self.p_refs = []

        self.id = None
        if 'id' in resource:
            self.id = resource['id']
        if 'member' in resource:
            for entity in resource['member']:
                self.p_refs.append(entity['entity']['reference'])
    
    def objectify(self, min=False):
        obj = { }

        for prop in ['resourceType', 'name', 'identifier', 'type', 'actual']:
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
        return self.resource['name']

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
                