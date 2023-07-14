"""
Provide support for summarizing demographics over a group of patients
"""
from collections import defaultdict
from summvar.fhir.codeableconcept import CodeableConcept
from summvar.fhir import MetaTag
from ncpi_fhir_plugin.common import constants
from pprint import pformat
import pdb

RACE_URL = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race"
races = [
    constants.RACE.NATIVE_AMERICAN,
    constants.RACE.ASIAN,
    constants.RACE.BLACK,
    constants.RACE.PACIFIC,
    constants.RACE.WHITE,
    constants.COMMON.OTHER,
    constants.COMMON.UNKNOWN
]

ETH_URL = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity"
ethnicities = [
    constants.ETHNICITY.HISPANIC,
    constants.ETHNICITY.NON_HISPANIC,
    constants.COMMON.OTHER,
    constants.COMMON.UNKNOWN
]

class RaceSummary:
    def __init__(self, name_prefix, group_ref, total_count):
        self.code =  CodeableConcept({      # CodeableConcept associated with this variable
            "coding": [{
                "system": "https://loinc.org/",
                "code": "32624-9",
                "display": "Race"
            }],
            "text": "Race"
        })
        self.name_prefix = name_prefix      # Group portion of the identity
        self.group_ref = group_ref          # Reference for use in focus
        self.total_count = total_count      # total number of group members
        self.race = defaultdict(set)
        self.value_codings = {}             # Stash the codings to be used to label observation components
        # Just to make sure we have a complete set of responses
        for race in races:
            self.race[race] = set()
            self.value_codings[race] = {
                "display": race
            }
    def add_reference(self, resource):
        #pdb.set_trace()
        if 'extension' in resource:
            for extension in resource['extension']:
                if extension['url'] == RACE_URL:
                    for extn2 in extension['extension']:

                        #pdb.set_trace()
                        race = extn2['valueCoding']['display']
                        if race == 'Unknown':
                            race = constants.COMMON.UNKNOWN
                        if race not in self.race:
                            print(f"New race encountered: {race}")
                            #pdb.set_trace()
                        self.race[race].add(f"Patient/{resource['id']}")
                        if 'code' not in self.value_codings[race]:
                            self.value_codings[race] = extn2['valueCoding']
                        return
    def objectify(self):
        entity = {
            'resourceType': 'Observation',
            'meta': {
                'tag': MetaTag()
            },
            'identifier': [ {
                'system': f"{constants.NCPI_DOMAIN}/variable-definition",
                'value': f"{self.name_prefix}-{self.code.display}"
            }, {
                'system': f'{constants.NCPI_DOMAIN}/study_group',
                'value': self.name_prefix
            }],
            'status': 'final',
            'code': {
                'coding': [{
                    'system': 'https://ncpi-fhir.github.io/ncpi-code-systems',
                    'code': 'Summary',
                    'display': "Variable Summary"
                }],
                'text': f"{self.code.display} Variable Summary"
            },
            'subject': {
                'reference': self.group_ref
            },
            'valueCodeableConcept': self.code.for_json(),
            'component': []
        }

        n = 0
        for race in self.race.keys():
            count = len(self.race[race])
            n += count
            component = {
                'code': {
                    'coding': [ self.value_codings[race]],
                    'text': f"Demographics ({self.code.display}): {race}"
                },
                'valueInteger': count
            }
            entity['component'].append(component)
        
        component = {
            'code': {
                'coding': [{
                    'system': "https://ncit.nci.nih.gov/ncitbrowser",
                    'code': 'C25697',
                    'display': "Sum"
                }],
                'text': f"Total Observations ({self.code.display})"
            },
            'valueInteger': n
        }
        entity['component'].append(component)

        component = {
            'code': {
                'coding': [{
                    'system': "https://ncit.nci.nih.gov/ncitbrowser",
                    'code': 'C54031',
                    'display': "Missing"
                }],
                'text': f"Number Missing ({self.code.display})"
            },
            'valueInteger': self.total_count - n
        }
        entity['component'].append(component)

        return entity
        
class EthSummary:
    def __init__(self, name_prefix, group_ref, total_count):
        self.code =  CodeableConcept({                      # CodeableConcept associated with this variable
            "coding": [{
                "system": "https://loinc.org/",
                "code": "69490-1",
                "display": "Ethnicity OMB.1997"
            }],
            "text": "Ethnicity"
        })
        self.name_prefix = name_prefix      # Group portion of the identity
        self.group_ref = group_ref          # Reference for use in focus
        self.total_count = total_count      # total number of group members
        self.eth = defaultdict(set)
        self.value_codings = {}             # Stash the codings to be used to label observation components
        # Just to make sure we have a complete set of responses       
        for eth in ethnicities:
            self.eth[eth] = set()
            self.value_codings[eth] = {
                "display": eth
            }

    def add_reference(self, resource):
        if 'extension' in resource:
            for extension in resource['extension']:
                if extension['url'] == ETH_URL:
                    for extn2 in extension['extension']:
                        if extn2['url'] == 'ombCategory':
                            eth = extn2['valueCoding']['display']
                            self.eth[eth].add(f"Patient/{resource['id']}")
                            if 'code' not in self.value_codings[eth]:
                                self.value_codings[eth] = extn2['valueCoding']
                            return
    def objectify(self):
        entity = {
            'resourceType': 'Observation',
            'meta': {
                'tag': MetaTag()
            },
            'identifier': [ {
                'system': f'{constants.NCPI_DOMAIN}/variable-definition',
                'value': f"{self.name_prefix}-{self.code.display}"
            }, {
                'system': f'{constants.NCPI_DOMAIN}/study_group',
                'value': self.name_prefix
            }],
            'status': 'final',
            'code': {
                'coding': [{
                    'system': 'https://ncpi-fhir.github.io/ncpi-code-systems',
                    'code': 'Summary',
                    'display': "Variable Summary"
                }],
                'text': f"{self.code.value} Variable Summary"
            },
            'subject': {
                'reference': self.group_ref
            },
            'valueCodeableConcept': self.code.for_json(),
            'component': []
        }

        n = 0
        for eth in self.eth.keys():
            count = len(self.eth[eth])
            n += count
            component = {
                'code': {
                    'coding': [ self.value_codings[eth]],
                    'text': f"Demographics ({self.code.display}): {eth}"
                },
                'valueInteger': count
            }
            entity['component'].append(component)
        
        component = {
            'code': {
                'coding': [{
                    'system': "https://ncit.nci.nih.gov/ncitbrowser",
                    'code': 'C25697',
                    'display': "Sum"
                }],
                'text': f"Total Observations ({self.code.display})"
            },
            'valueInteger': n
        }
        entity['component'].append(component)

        component = {
            'code': {
                'coding': [{
                    'system': "https://ncit.nci.nih.gov/ncitbrowser",
                    'code': 'C54031',
                    'display': "Missing"
                }],
                'text': f"Number Missing ({self.code.display})"
            },
            'valueInteger': self.total_count - n
        }
        entity['component'].append(component)

        return entity


class GenderSummary:
    def __init__(self, name_prefix, group_ref, total_count):
        self.code = CodeableConcept({                      # CodeableConcept associated with this variable
            "coding": [ {
                "system": "https://loinc.org/",
                "code": "46098-0",
                "display": "sex"
            }],
            "text": "Gender"
        })     
        self.name_prefix = name_prefix      # Group portion of the identity
        self.group_ref = group_ref          # Reference for use in focus
        self.total_count = total_count      # total number of group members
        self.value_codings = {              # Stash the codings to be used to label observation components
            "male": {
                "system": "http://hl7.org/fhir/ValueSet/administrative-gender",
                "code": "male",
                "display": "Male"
            },
            "female": {
                "system": "http://hl7.org/fhir/ValueSet/administrative-gender", 
                "code": "female",
                "display": "Female"
            },
            "other": {
                "system": "http://hl7.org/fhir/ValueSet/administrative-gender", 
                "code": "other",
                "display": "Other"
            },
            "unknown": {
                "system": "http://hl7.org/fhir/ValueSet/administrative-gender", 
                "code": "unknown",
                "display": "Unknown"
            }
        }
        self.gender = {
            "male": set(),
            "female": set(),
            "other": set(),
            "unknown": set()
        }

    def add_reference(self, resource):
        if 'gender' in resource:
            gender = resource['gender']
            self.gender[gender].add(f"Patient/{resource['id']}")

    def objectify(self):
        entity = {
            'resourceType': 'Observation',
            'meta': {
                'tag': MetaTag()
            },
            'identifier': [ {
                'system': f'{constants.NCPI_DOMAIN}/variable-definition',
                'value': f"{self.name_prefix}-{self.code.display}"
            }, {
                'system': f'{constants.NCPI_DOMAIN}/study_group',
                'value': self.name_prefix
            }],
            'status': 'final',
            'code': {
                'coding': [{
                    'system': 'https://ncpi-fhir.github.io/ncpi-code-systems',
                    'code': 'Summary',
                    'display': "Variable Summary"
                }],
                'text': f"{self.code.display} Variable Summary"
            },
            'subject': {
                'reference': self.group_ref
            },
            'valueCodeableConcept': self.code.for_json(),
            'component': []
        }

        n = 0
        for gender in self.gender.keys():
            count = len(self.gender[gender])
            n += count
            component = {
                'code': {
                    'coding': [ self.value_codings[gender]],
                    'text': f"Demographics (Sex): {gender}"
                },
                'valueInteger': count
            }
            entity['component'].append(component)
        
        component = {
            'code': {
                'coding': [{
                    'system': "https://ncit.nci.nih.gov/ncitbrowser",
                    'code': 'C25697',
                    'display': "Sum"
                }],
                'text': f"Total Observations ({self.code.display})"
            },
            'valueInteger': n
        }
        entity['component'].append(component)

        component = {
            'code': {
                'coding': [{
                    'system': "https://ncit.nci.nih.gov/ncitbrowser",
                    'code': 'C54031',
                    'display': "Missing"
                }],
                'text': f"Number Missing ({self.code.display})"
            },
            'valueInteger': self.total_count - n
        }
        entity['component'].append(component)

        return entity
def summarize(client, name_prefix, patient_refs, group_ref):
    genders = GenderSummary(name_prefix, group_ref, len(patient_refs))
    eths = EthSummary(name_prefix, group_ref, len(patient_refs))
    races = RaceSummary(name_prefix, group_ref, len(patient_refs))
    for ref in patient_refs:
        response = client.get(ref)
        if response.success():
            for entry in response.entries:
                resource = entry
                if 'resource' in entry:
                    resource = entry['resource']
                genders.add_reference(resource)
                eths.add_reference(resource)
                races.add_reference(resource)

    return [genders.objectify(), eths.objectify(), races.objectify()]