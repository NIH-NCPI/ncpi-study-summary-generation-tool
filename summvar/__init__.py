__version__="0.1.0"

import pdb

from summvar.fhir import MetaTag

_system_prefix="https://defaultserver.com/fhir"
# We will eventually create profiles for each of our study types, but those 
# haven't been created yet, so we'll just use bare profiles
_research_study_profile = None
_dbgap_study_url = "https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id="

_valid_phs_ids = set()

def system_prefix(prefix=None):
    global _system_prefix 

    if prefix is not None:
        _system_prefix = prefix
    return _system_prefix

def system_url(consortium_id=None, table_name=None, study_id=None, dataset_id=None):
    components = [system_prefix()]

    if consortium_id is not None:
        components.append(consortium_id)

    if table_name is not None:
        components.append(table_name)

    if study_id is not None:
        components.append(study_id)
    
    if dataset_id is not None:
        components.append(dataset_id)

    return "/".join(components)

def study_id(consortium, study_id, dataset_name):
    id = []

    if consortium is not None:
        id.append(consortium)

    if study_id is not None:
        id.append(study_id)
    if dataset_name is not None:
        id.append(dataset_name)

    return ".".join([x.replace('-', '.').replace("_", ".") for x in id])

def create_study_group(study, dataset_name, member_count=0):
    if member_count is None:
        member_count = 0
    if dataset_name is not None:
        tag = {
            'system': system_url(study_id=study, table_name="study-group"),
            'code': dataset_name
        }
        identifier = [{
            'system': system_url(study, table_name="study-group"),
            'value': dataset_name
        }]
    else:
        tag = {
            'system': _dbgap_study_url,
            'code': study
        }
        identifier = [{
            'system': system_url("dbgap", table_name="study-group"),
            'value': study
        }]
    obj = {
        'meta': {
            'tag': [tag],
            'profile': [
                "https://nih-ncpi.github.io/ncpi-fhir-ig/StructureDefinition/study-group"
            ]
        },
        "resourceType": "Group",        
        'identifier': identifier,
        "type": "person",
        "actual": True,
        "quantity": member_count
    }

    return obj

def create_dataset_study(consortium, 
                         study, 
                         dataset_name, 
                         title, 
                         web_url, 
                         description):
    global _research_study_profile, _valid_phs_ids

    if title is None:
        title = dataset_name

    if dataset_name is not None:
        tag = {
            'system': system_url(study_id=study),
            'code': dataset_name
        }
        identifier = [{
            'system': system_url(study),
            'value': dataset_name
        }]
        id = study_id(consortium=consortium, 
                  study_id=study, 
                  dataset_name=dataset_name).replace(".", "-")
    else:
        tag = {
            'system': _dbgap_study_url,
            'code': study
        }
        identifier = [{
            'system': _dbgap_study_url,
            'value': study
        }]
        id = study

    # I guess these workspace names are too long for SMILES fhir id
    if id[:3] != "phs":
        id = None
    obj = {
        'meta': {
            'tag': [tag],
            'profile': [
                "https://nih-ncpi.github.io/ncpi-fhir-ig/StructureDefinition/ncpi-research-study"
            ]
        },
        "resourceType": "ResearchStudy",
        "status": "completed",
        'identifier': identifier,
        'title': title, 
        "description": description
            
    }
    if id is not None:
        obj['id'] = id

    if id is not None:
        _valid_phs_ids.add(id)

    if web_url is not None:
        obj['relatedArtifact'] = [{
            "type": "documentation",
            "label": "Study Website", 
            "url": web_url
        }]

    if _research_study_profile is not None:
        obj['meta']['profile'] = _research_study_profile

    #invalid_studies = [None, "", "phs001155"]
    if study in _valid_phs_ids and dataset_name is not None:
        obj['partOf'] = [{
            "reference": f"ResearchStudy/{study}"
        }]

    return obj

def fix_fieldname(fieldname):
    """We can't trust humans to be particularly consistent and some """
    """'creative' habits are not particularly great for using as """
    """identifiers so we must strip that stuff out to ensure consistency."""
    return fieldname.lower().replace(" ", "_").replace(")", "").replace("(", "").replace("/", "_")


class MissingIdentifier(Exception):
    def __init__(self, resource_type):
        super().__init__(f"Invalid Request: The resource, {resource_type} must have either an identifier or a resource")
        self.resource_type = resource_type

class BadIdentifier(Exception):
    def __init__(self, resource_type, identifier):
        super().__init__(f"Bad Identifier: No match found for {resource_type}.identifier == {identifier}")
        self.resource_type = resource_type
        self.identifier = identifier