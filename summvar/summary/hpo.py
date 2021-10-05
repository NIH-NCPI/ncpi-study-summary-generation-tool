"""
Provide support for summarizing HPO Observations over a group of patients
"""

from collections import defaultdict
from summvar.fhir.codeableconcept import CodeableConcept
import pdb
from pprint import pformat

ncpi_phenotype = "http://fhir.ncpi-project-forge.io/StructureDefinition/ncpi-phenotype"
status_lkup = {
    "373573001": "Present",
    "373572006": "Absent",
    "POS": "Present",
    "NEG": "Absent",
    "confirmed": "Present",
    "refuted": "Absent"
}

code_lkup = {
    "Present": "373573001",
    "Absent": "373572006"
}

class ObservationSummary:
    def __init__(self, code, name_prefix, group_ref, total_count):
        self.code = code                    # CodeableConcept associated with this variable
        self.name_prefix = name_prefix      # Group portion of the identity
        self.group_ref = group_ref          # Reference for use in focus
        self.total_count = total_count      # total number of group members
        self.status_refs = defaultdict(set) # Present => N, Absent => N

    def add_reference(self, resource):
        # Not sure if everyone is doing both interpretation and valueCC
        if 'interpretation' in resource:
            cc = CodeableConcept(resource['interpretation'][0])
        else:
            cc = CodeableConcept(resource['valueCodeableConcept'])

        status = cc.value
        if status in status_lkup:
            status = status_lkup[status]
        if status is None:
            print(pformat(resource))
            pdb.set_trace()
        self.status_refs[status].add(resource['subject']['reference'])

    def to_json(self):
        entity = {
            'resourceType': 'Observation',
            'identifier': [ {
                'system': 'https://ncpi-fhir.github.io/variable-definition',
                'value': f"{self.name_prefix}-{self.code.value}"
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
            component = {
                'code': {
                    'coding': [{
                        'system': "http://snomed.info/sct",
                        'code': code_lkup[status],
                        'display': status
                    }],
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
        response = client.get(f"Observation?subject={ref}&_profile={ncpi_phenotype}")
        if response.success():
            for entry in response.entries:
                resource = entry['resource']
                cc = CodeableConcept(resource['code'])
                code = cc.code

                if code not in observations:
                    observations[code] = ObservationSummary(cc, name_prefix, group_ref, total_count = len(patient_refs))

                observations[code].add_reference(resource)

    summaries = []
    for code in observations.keys():
        summaries.append(observations[code].to_json())
    return summaries