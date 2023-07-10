"""
A Set of codes that will be used for common components like Total, Min, Max, Race, Gender, etc. These should not include detail level codings for things like a specific race or gender as those will be pulled from the source data. 
"""

NCIT = "https://uts.nlm.nih.gov/uts/umls"
LOINC = "https://loinc.org"
UCUM = "https://unitsofmeasure.org"

common_terms = None

def add_common_term(key, system, code, display):
    global common_terms
    if common_terms is None:
        common_terms = {}

    common_terms[key] = {
            "system": system,
            "code": code, 
            "display": display
    }

add_common_term("COUNT", NCIT, "C0750480", "Count")
add_common_term("DISTINCT", NCIT, "C3641802", "Distinct Product Count")
add_common_term("SUM", NCIT, "C25697", "Sum")
add_common_term("MEAN", NCIT, "C0444504", "Statistical Mean")
add_common_term("RANGE", NCIT, "C2348147", "Sample Range")
add_common_term("SUMMARY_REPORT", NCIT, "C0242482", "Summary Report")
add_common_term("GENDER", NCIT, "C0079399", "Gender")
add_common_term("MISSING", NCIT, "C142610", "Missing Data")
add_common_term("INVALID", NCIT, "C3245471", "Invalid")

