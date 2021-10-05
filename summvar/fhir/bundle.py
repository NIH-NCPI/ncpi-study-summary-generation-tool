"""
Abstraction for creating FHIR bundles
"""

class TransactionBundle:
    def __init__(self, bundle_id, fhir_host):
        self.id = bundle_id
        self.host = fhir_host
        self.entries = []

    def add_post(self, resource_object):
        self.entries.append(resource_object)
    
    def objectify(self):
        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": []
        }

        for entry in self.entries:
            bundle.entry.append({
                "fullUrl": f"{self.host.target_service_url}/{entry.reference}",
                "resource": entry.resource,
                "url": f'"{entry.resource_type}"'
            })

        return bundle