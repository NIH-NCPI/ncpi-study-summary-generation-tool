"""
Provide support for summarizing conditions over a group of patients
"""

from collections import defaultdict
from summvar.fhir.codeableconcept import CodeableConcept
from ncpi_fhir_plugin.common import constants

from pprint import pformat
import pdb

ncpi_phenotype = "https://ncpi-fhir.github.io/ncpi-fhir-ig/StructureDefinition/phenotype"
status_lkup = {
    "373573001": "Present",
    "373572006": "Absent",
    "POS": "Present",
    "NEG": "Absent",
    "confirmed": "Present",
    "refuted": "Absent",
    "provisional": "Possibly affected"
}

#  http://terminology.hl7.org/CodeSystem/condition-ver-status
code_lkup = {
    "Present": "confirmed",
    "Absent": "refuted"
}

class ConditionSummary:
    def __init__(self, code, name_prefix, group_ref, total_count):
        self.code = code                    # CodeableConcept associated with this variable
        self.name_prefix = name_prefix      # Group portion of the identity
        self.group_ref = group_ref          # Reference for use in focus
        self.total_count = total_count      # total number of group members
        self.status_refs = defaultdict(set) # Present => N, Absent => N

        for status in code_lkup.keys():
            self.status_refs[status] = set()

    def add_reference(self, resource):
        # Not sure if everyone is doing both interpretation and valueCC
        cc = CodeableConcept(resource['verificationStatus'])

        status = cc.value
        if status in status_lkup:
            status = status_lkup[status]
        self.status_refs[status].add(resource['subject']['reference'])


    def to_json(self):
        value = self.code.value

        if len(value) > 150:
            value = value[0:150]
        entity = {
            'resourceType': 'Observation',
            'identifier': [ {
                'system': 'https://ncpi-fhir.github.io/variable-definition',
                'value': f"{self.name_prefix}-{value}"
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
                'text': "Variable Summary"
            },
            'subject': {
                'reference': self.group_ref
            },
            'valueCodeableConcept': self.code.for_json(),
            'component': []
        }

        n = 0
        for status in self.status_refs.keys():
            count = len(self.status_refs[status])
            n += count
            if status in code_lkup:
                component = {
                    'code': {
                        'coding': [{
                            'system': "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                            'code': code_lkup[status],
                            'display': status
                        }],
                        'text': f"Phenotype {status}"
                    },
                    'valueInteger': count
                }
            else:
                component = {
                    'code': {
                        'text': f"Phenotype {status}"
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
                'text': f"Total Observations"
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
                'text': f"Number Missing Phenotype"
            },
            'valueInteger': self.total_count - n
        }
        entity['component'].append(component)

        return entity

def summarize(client, name_prefix, patient_refs, group_ref):
    observations = {}
    for ref in patient_refs:
        #pdb.set_trace()
        entry_count = 0
        response = client.get(f"Condition?subject={ref}&_profile={ncpi_phenotype}")
        if response.success():
            for entry in response.entries:
                resource = entry['resource']
                cc = CodeableConcept(resource['code'])
                code = cc.code
                entry_count += 1
                if code not in observations:
                    observations[code] = ConditionSummary(cc, name_prefix, group_ref, total_count = len(patient_refs))

                observations[code].add_reference(resource)
        if entry_count > 0:
            print(f"{entry_count} - Condition?subject={ref}&_profile={ncpi_phenotype}")

    summaries = []
    for code in observations.keys():
        summaries.append(observations[code].to_json())
    return summaries