__version__="0.1.0"

class MissingIdentifier(Exception):
    def __init__(self, resource_type):
        super().__init__(f"Invalid Request: The resource, {resource_type} must have either an identifier or a resource")
        self.resource_type = resource_type

class BadIdentifier(Exception):
    def __init__(self, resource_type, identifier):
        super().__init__(f"Bad Identifier: No match found for {resource_type}.identifier == {identifier}")
        self.resource_type = resource_type
        self.identifier = identifier