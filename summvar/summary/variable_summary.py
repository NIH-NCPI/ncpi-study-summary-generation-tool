"""
Provide the basic scaffolding for a Variable Summary resource. 

Client classes will populate the components and properties according to their need which can then be compiled into a compliant FHIR resource. 
"""

from collections import defaultdict
from summvar.summary.constants import common_terms
from summvar.fhir.codeableconcept import CodeableConcept
from summvar.summary import _VARDEF_SYSTEM, _VARDEF_PROFILE

from summvar.fhir import MetaTag

class VariableSummary:
    def __init__(self, name_prefix, code, population):
        self.code = code            # CodeableConcept to be used to tie the summary back to the originating ObservationDefinition

        # name_prefix used for identifier
        self.name_prefix = name_prefix

        # Population is the SummaryGroup associated with this summary variable
        self.population = population
        self.codings = {}           # Code => Coding

        # code => count
        self.counts = defaultdict(int)
        self.quantities = {}

    def objectify(self):
        value = self.code.value

        if len(value) > 150:
            value = value[0:150]
        return {
            'resourceType': 'Observation',
            'meta': {
                'profile': [
                    _VARDEF_PROFILE
                ],
                'tag': MetaTag()
            },
            'identifier': [ {
                'system': _VARDEF_SYSTEM,
                'value': f"{self.name_prefix}-{value}"
            }],
            'status': 'final',
            'code': {
                'coding': [common_terms['SUMMARY_REPORT']],
                'text': common_terms['SUMMARY_REPORT']['display']
            },
            'subject': {
                'reference': self.population.reference
            },
            'valueCodeableConcept': self.code.for_json(),
            'component': []
        }
