"""
Abstraction for FHIR resource, ObservationDefinition
"""
from summvar import MissingIdentifier, BadIdentifier
from rich.pretty import pprint
from copy import deepcopy
from collections import defaultdict
from summvar.fhir.codeableconcept import CodeableConcept
from summvar.summary.constants import common_terms
from summvar.summary.variable_summary import VariableSummary
import sys
import pdb

class QuantityVariable:
    def __init__(self, unit, unit_code, unit_system):
        self.sum = 0
        self.count = 0
        self.min = None
        self.max = None

        self.unit = unit 
        self.unit_code = unit_code
        self.unit_system = unit_system

    def add_quantity(self, quantity):
        if self.min is None or quantity < self.min:
            self.min = quantity
        if self.max is None or quantity > self.max:
            self.max = quantity

        self.count += 1
        self.sum += quantity

    def mean(self):
        rval = {
            'value': self.sum / self.count
        }
        if self.unit is not None:
            rval['unit'] = self.unit
        
        if self.unit_code is not None:
            rval['code'] = self.unit_code
        
        if self.unit_system is not None:
            rval['system'] = self.unit_system
    
        return rval

    def add_min_max(self, resource):
        if self.min is not None and self.max is not None and self.min != self.max:
            resource['valueRange'] = {
                'low': {
                    'value': self.min
                },
                'high': {
                    'value': self.max
                }
            }
            if self.unit is not None:
                resource['valueRange']['low']['unit'] = self.unit
                resource['valueRange']['high']['unit'] = self.unit
            
            if self.unit_code is not None:
                resource['valueRange']['low']['code'] = self.unit_code
                resource['valueRange']['high']['code'] = self.unit_code
            
            if self.unit_system is not None:
                resource['valueRange']['low']['system'] = self.unit_system
                resource['valueRange']['high']['system'] = self.unit_system

class DefaultSummary:
    def __init__(self, permittedDataTypes):
        self.permittedDataTypes = permittedDataTypes
        self.observed_data = defaultdict(int)
        self.missing = 0
        self.total_nonmissing = 0
        self.type_name = "String"

    @property 
    def missing_count(self):
        return self.missing
    
    @property
    def nonmissing_count(self):
        return self.total_nonmissing

    def get_vocabulary(self, client):
        return None

    def add_resource(self, resource):
        if 'valueString' in resource:
            self.observed_data[resource['valueString']] += 1
            self.total_nonmissing += 1
        else:
            self.missing += 1

    def summarize(self, var_summary):
        pdb.set_trace()
        # For these, we'll report distinct values, total non-missing and missing values
        component = {
            'code': {
                'coding': [common_terms['COUNT']],
                'text': common_terms['COUNT']['display']
            },
            'valueInteger': self.total_nonmissing
        }
        var_summary['component'].append(component)

        component = {
            'code': {
                'coding': [common_terms['DISTINCT']],
                'text': common_terms['DISTINCT']['display']
            },
            'valueInteger': len(self.observed_data)
        }
        var_summary['component'].append(component)

        component = {
            'code': {
                'coding': [common_terms['MISSING']],
                'text': common_terms['MISSING']['display']
            },
            'valueInteger': self.missing
        }
        var_summary['component'].append(component)

    def update_obj(self, obj, remote_host):
        return obj

class DateTimeSummary:
    def __init__(self, permittedDataTypes):
        self.permittedDataTypes = permittedDataTypes
        self.observed_data = defaultdict(int)
        self.missing = 0
        self.total_nonmissing = 0
        self.type_name = "String"

    @property 
    def missing_count(self):
        return self.missing
    
    @property
    def nonmissing_count(self):
        return self.total_nonmissing

    def get_vocabulary(self, client):
        return None

    def add_resource(self, resource):
        if '_valueDateTime' in resource:
            ext = resource['_valueDateTime']

            #pdb.set_trace()
            offset = ext['extension'][0]['extension'][3]['valueDuration']['value']
            self.observed_data[offset] += 1
            self.total_nonmissing += 1
        else:
            self.missing += 1

    def summarize(self, var_summary):
        # For these, we'll report distinct values, total non-missing and missing values
        component = {
            'code': {
                'coding': [common_terms['COUNT']],
                'text': common_terms['COUNT']['display']
            },
            'valueInteger': self.total_nonmissing
        }
        var_summary['component'].append(component)

        component = {
            'code': {
                'coding': [common_terms['DISTINCT']],
                'text': common_terms['DISTINCT']['display']
            },
            'valueInteger': len(self.observed_data)
        }
        var_summary['component'].append(component)

        component = {
            'code': {
                'coding': [common_terms['MISSING']],
                'text': common_terms['MISSING']['display']
            },
            'valueInteger': self.missing
        }
        var_summary['component'].append(component)

    def update_obj(self, obj, remote_host):
        return obj
class QuantitySummary:
    def __init__(self, permittedDataTypes):
        self.permittedDataTypes = permittedDataTypes
        self.quantity = None
        self.codeableconcept = None
        self.missing = 0
        self.observations_observed = 0
        self.type_name = "Quantity"

    @property 
    def missing_count(self):
        return self.missing
    
    @property
    def nonmissing_count(self):
        if self.quantity is not None:
            return self.quantity.count
        return 0

    def get_vocabulary(self, client):
        return None

    def add_resource(self, resource):
        self.observations_observed += 1
        try:
            quant = resource['valueQuantity']
            if self.quantity is None:
                self.codeableconcept = resource['code']
                self.quantity = QuantityVariable(unit=quant.get('unit'), 
                                                    unit_code=quant.get('code'), 
                                                    unit_system=quant.get('system'))
            self.quantity.add_quantity(float(quant['value']))
        except:
            self.missing += 1


    def summarize(self, var_summary):
        if self.codeableconcept is not None:
            cc = self.codeableconcept
            if 'coding' in cc:
                cc = self.codeableconcept['coding'][0]
            if 'display' not in cc:
                if 'code' not in cc:
                    print(cc)
                    pdb.set_trace()
                text = cc['code']
            else:
                text = cc['display']
            component = {
                'code': {
                    'coding': [common_terms['COUNT']],
                    'text': common_terms['COUNT']['display']
                },
                'valueInteger': self.quantity.count
            }
            var_summary['component'].append(component)
            component = {
                'code': {
                    'coding': [common_terms['MEAN']],
                    'text': common_terms['MEAN']['display']
                },
                'valueQuantity': self.quantity.mean()
            }
            var_summary['component'].append(component)

            component = {
                'code': {
                    'coding': [common_terms['RANGE']],
                    'text': common_terms['RANGE']['display']
                },
            }
            self.quantity.add_min_max(component)
            if 'valueRange' in component:
                var_summary['component'].append(component)

        missing = {
            'code': {
                'coding': [common_terms['MISSING']],
                'text': common_terms['MISSING']['display']
            },
            'valueInteger': self.missing
        }
        var_summary['component'].append(missing)
    def update_obj(self, obj, remote_host):
        return obj

class CodeableConceptSummary:
    def __init__(self, client, valueset_ref, permittedDataTypes):
        self.permittedDataTypes = permittedDataTypes
        self.codings = {}
        self.observations = defaultdict(int)
        self.missing = 0 
        self.non_missing = 0
        self.valueset_ref = valueset_ref
        self.type_name = "CodeableConcept"

        response = client.get(f"{valueset_ref}/$expand")

        if response.success() and len(response.entries) > 0:
            entry = response.entries[0]

            if 'resource' in entry:
                entry = entry['resource']
            vs = entry

            for coding in vs['expansion']['contains']:
                self.codings[coding['code']] = coding
                self.observations[coding['code']] = 0

        # When you expand the valueset, the url is lost...
        response = client.get(valueset_ref)
        if response.success() and len(response.entries) > 0:
            entry = response.entries[0]
            if 'resource' in entry:
                entry = entry['resource']
            
            self.valueset_url = entry['url']

    @property 
    def missing_count(self):
        return self.missing
    
    @property
    def nonmissing_count(self):
        return self.non_missing

    def update_obj(self, obj, remote_host):
        response = remote_host.get(f"ValueSet?url={self.valueset_url}")
        if response.success():
            resource = response.entries[0]

            if 'resource' in resource:
                resource = resource['resource']

            obj['validCodedValueSet']['reference'] = f"ValueSet/{resource['id']}"
        return obj


    def get_vocabulary(self, client):
        vocabulary = None
        response = client.get(f"{self.valueset_ref}")

        if response.success():
            vocabulary = {}
            # Should only be one since it's a reference
            resource = response.entries[0]
            if 'resource' in resource:
                resource = resource['resource']

            vocabulary[resource['url']] = resource

            if 'compose' in resource:
                if 'include' in resource['compose']:
                    for incl in resource['compose']['include']:
                        url = incl['system']
                        response = client.get(f"CodeSystem?url={url}")

                        if response.success():
                            if len(response.entries) != 1:
                                print(f"The query for VS code system yielded {len(response.entries)} responses: CodeSystem?url={url}")
                            resource = response.entries[0]

                            if 'resource' in resource:
                                resource = resource['resource']
                            vocabulary[url] = resource
        
        return vocabulary

    def add_resource(self, resource):
        if 'valueCodeableConcept' in resource:
            if 'coding' not in resource['valueCodeableConcept']:
                self.observations[resource['valueCodeableConcept']['text']] += 1
            else:
                self.observations[resource['valueCodeableConcept']['coding'][0]['code']] += 1
            self.non_missing += 1
        else:
            self.missing += 1
    
    def summarize(self, var_summary):
        for code in sorted(self.codings.keys()):
            component = {
                'code': {
                    'coding': [self.codings[code]],
                    'text': self.codings[code]['display']
                },
                'valueInteger': self.observations[code]
            }
            var_summary['component'].append(component)
        
        component = {
            'code': {
                'coding': [common_terms['MISSING']],
                'text': common_terms['MISSING']['display']
            },
            'valueInteger': self.missing
        }
        var_summary['component'].append(component)

class ObservationDefinition:
    def __init__(self, client, resource=None, identifier=None):
        self.client = client
        self.resource_type = "ObservationDefinition"
        self.vocabulary = None

        if resource is None:
            if identifier is None:
                raise MissingIdentifier(self.resource_type)

            resource = self.pull_details(identifier)
            if resource is None:
                raise BadIdentifier(self.resource_type, identifier)

        self.data_manager = None
        self.population = None
        self.resource = resource
        self.id = resource['id']
        self.identifier = resource['identifier'][0]
        self.code = CodeableConcept(resource['code'])
        self.name_prefix = f"{self.identifier['value']}-VariableSummary"
        self.init_data_manager()
        self.valid_observation_count = 0

        self.remote_ref = None

    @property
    def type_name(self):
        return self.data_manager.type_name

    @property
    def nonmissing_count(self):
        return self.data_manager.nonmissing_count

    @property
    def missing_count(self):
        return self.data_manager.missing_count

    @property
    def source_identifier(self):
        return f"{self.identifier['system']}|{self.identifier['value']}"

    def objectify(self, remote_host=None):
        obj = {}

        for prop in ['meta', 'identifier', 'code', 'permittedDataType', 'validCodedValueSet', 'quantitativeDetails', 'qualifiedInterval', 'resourceType', 'category']:
            if prop in self.resource:
                obj[prop] = deepcopy(self.resource[prop])
        if remote_host is not None:
            obj = self.data_manager.update_obj(obj, remote_host=remote_host)
        return obj


    def load(self, remote_host):
        resource = self.objectify(remote_host)
        identifier = f"{resource['identifier'][0]['system']}|{resource['identifier'][0]['value']}"
        response = remote_host.post(resource['resourceType'], resource, identifier=identifier)
        if response['status_code'] > 299:
            pprint(resource)
            resource
            pprint(response['response'])
            print(response['status_code'])
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

    def get_vocabulary(self):
        return self.data_manager.get_vocabulary(self.client)

    def pull_observations(self, population):
        # Reset the data manager in case we are rerunning on a different population
        self.init_data_manager()
        self.population = population
        coding = self.code.coding[0]

        self.valid_observation_count = 0
        query = f"Observation?code={coding['system']}|{coding['code']}"
        response = self.client.get(query)

        if response.success() and len(response.entries) > 0:
            for resource in response.entries:
                if 'resource' in resource:
                    resource = resource['resource']
                if 'subject' not in resource:
                    pdb.set_trace()
                subject = resource['subject']['reference']

                # Ignore anything that isn't in the target population
                if self.population.is_member(subject):

                    self.valid_observation_count += 1
                    if 'resource' in resource:
                        resource = resource['resource']
                    self.data_manager.add_resource(resource)

    def pull_details(self, odref):
        # ObjectDefinition doesn't currently support querying by identifier,
        # so we must assume that the input is a reference
        assert(odref.split("/")[0] == self.resource_type)

        response = self.client.get(odref)
        if response.success():
            resource = response.entries[0]['resource']

            self.id = resource['id']
            self.resource = resource
            self.identifier = resource['identifier'][0]

            self.init_data_manager()

    def build_summary(self, remote_host):
        variable_summary = None
        if self.valid_observation_count > 0:
            vs = VariableSummary(self.name_prefix, population=self.population, code=self.code)
            variable_summary = vs.objectify()
            variable_summary['subject'] = {
                'reference': self.population.remote_reference(remote_host)
            }
            self.data_manager.summarize(variable_summary)

        return variable_summary

    def init_data_manager(self):
        permittedDataTypes = self.resource['permittedDataType']
        self.population = None
        if "CodeableConcept" in permittedDataTypes:
            if 'validCodedValueSet' not in self.resource:
                print(f"The OD {self.identifier['value']} is labeled as to accept codes as values, but doesn't have the validCodedValueSet")
                print("Using DefaultSummary instead of CodeableConcept")
                self.data_manager = DefaultSummary(permittedDataTypes)
            else:
                self.data_manager = CodeableConceptSummary(self.client, self.resource['validCodedValueSet']['reference'], permittedDataTypes)
        elif "Quantity" in permittedDataTypes:
            self.data_manager = QuantitySummary(permittedDataTypes)
        elif "string" in permittedDataTypes:
            self.data_manager = DefaultSummary(permittedDataTypes)
        elif "dateTime" in permittedDataTypes:
            self.data_manager = DateTimeSummary(permittedDataTypes)
        else:
            print(f"No familiar data types found in {permittedDataTypes}. Using default (string)")
            self.data_manager = DefaultSummary(permittedDataTypes)
        
