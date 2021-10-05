


class CodeableConcept:
    def __init__(self, cc):
        self.text = cc.get('text')
        self.coding = cc.get('coding')

    @property
    def value(self):
        code = self.code
        if code is None:
            return self.text
        return code
    
    @property
    def display(self):
        if 'display' in self.coding:
            return self.coding['display']
        return self.text

    @property 
    def system(self):
        if self.coding is not None:
            return self.coding[0]['system']  
        return None      

    @property
    def code(self):
        if self.coding is not None:
            return self.coding[0]['code']
        return None

    def for_json(self):
        return {
            "coding": self.coding,
            "text": self.text
        }