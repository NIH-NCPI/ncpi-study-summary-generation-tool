"""
Abstraction for the Fhir Observation holding the summary data
"""

varsum_code = {
    'coding': [{
        'system': 'https://ncpi-fhir.github.io/ncpi-code-systems',
        'code': 'Summary',
        'display': "Variable Summary"
    }],
    'text': "Variable Summary"
}

class SummaryObservation:
    def __init__(self, host, name, group, code):
        self.host = host
        self.resource_type = 'Observation'
        self.name = name
        self.group_ref = group
        self.code = code
        self.components = []

    @property
    def reference(self):
        return f"{self.resource_type}/{self.name}"

    def add_integer_component(self, code, value):
        component = {
            'code': code,
            'valueInteger': value
        }
        self.components.append(component) 

    def objectify(self):
        entity = {
            'resourceType': self.resourceType, 
            'identifier': [{
                'system': 'https://ncpi-fhir.github.io/variable-definition',
                'value': self.name
            }],
            'status': 'final',
            'code': varsum_code,
            'subject': {
                'reference': self.group.reference
            },
            'valueCodeableConcept': self.code.objectify()
        }

    