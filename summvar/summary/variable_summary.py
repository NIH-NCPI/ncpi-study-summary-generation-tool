"""
Provide the basic scaffolding for a Variable Summary resource. 

Client classes will populate the components and properties according to their need which can then be compiled into a compliant FHIR resource. 
"""

from collections import defaultdict
from summvar.summary.constants import common_terms
from summvar.fhir.codeableconcept import CodeableConcept
from summvar.summary import _VARDEF_SYSTEM, _VARDEF_PROFILE
from summvar import system_url

from summvar.fhir import MetaTag

class VariableSummary:
    def __init__(self, study_id, dataset_name, name_prefix, code, population, focus):
        self.code = code            # CodeableConcept to be used to tie the summary back to the originating ObservationDefinition

        self.system_url = system_url(study_id=study_id, dataset_id=dataset_name)

        # name_prefix used for identifier. This should be relate back to the 
        # data dictionary variable name for variable summaries. 
        self.name_prefix = name_prefix

        # Population is the SummaryGroup associated with this summary variable
        self.population = population
        self.codings = {}           # Code => Coding

        self.focus = focus

        # code => count
        self.counts = defaultdict(int)
        self.quantities = {}

    def objectify(self):
        value = self.code.value

        if len(value) > 150:
            value = value[0:150]

        return_value = {
            'resourceType': 'Observation',
            'meta': {
                'tag': MetaTag()
            },
            'identifier': [ {
                'system': self.system_url,
                'value': f"{self.name_prefix}-{value}"
            }],
            'status': 'final',
            'code': {
                'coding': [common_terms['SUMMARY_REPORT']],
                'text': common_terms['SUMMARY_REPORT']['display']
            },
            'focus': [{
                'reference':  self.focus
            }],
            'valueCodeableConcept': self.code.for_json(),
            'component': []
        }

        if _VARDEF_PROFILE:
            return_value['meta']['profile'] = [_VARDEF_PROFILE]

        if self.population is not None:
            return_value['subject'] = """{
                'reference': self.population.reference
            }"""

        return return_value
