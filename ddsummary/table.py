from datetime.datetime import now

class Table:
    def __init__(self, name, source_date=None):
        # Table's name
        self.name = name

        # Fieldnames that were fully summarized
        self.fields_summarized = []

        # Fields that were found in the source data table that were not 
        # found in the data-dictionary
        self.unrecognized_fields = []

        # Just a log of any fields that were found in the data-dictionary
        # but not found in the source data table
        self.missing_fields = []

        # Date when the data in the source table was last modified
        self.source_date = source_date

        # Date when the summary was last performed
        self.summary_date = None

    def summarized_field(self, fieldname, summary_date=None):
        self.fields_summarized.append(fieldname)
        
        if summary_date is None:
            summary_date = now()

        self.summary_date = summary_date

    def add_unrecognized_field(self, fieldname):
        self.unrecognized_fields.append(fieldname)

    def add_missing_field(self, fieldname):
        self.missing_fields.append(fieldname)
