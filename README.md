# Summarize FHIR Variables 
This project is an early version of a tool that pulls data from a FHIR server and builds Summary data based on a small number of demographic variables (from the Patient records) and Phenotypes.

For Phenotype data, the tool assumes that the data follows the [NCPI-FHIR-IG](https://github.com/NIH-NCPI/ncpi-fhir-ig) [Phenotype](https://github.com/NIH-NCPI/ncpi-fhir-ig/blob/main/input/fsh/Profile-Phenotype.fsh) profile. We plan to add in support for the NCPI [Disease](https://github.com/NIH-NCPI/ncpi-fhir-ig/blob/main/input/fsh/Profile-Disease.fsh) and unprofiled Conditions as well in the future. 

For Patient demographics, the system assumes the use of [us-core-race](http://hl7.org/fhir/us/core/StructureDefinition/us-core-race) and [us-core-ethnicity](http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity) extensions on the Patient resource record. For gender, just the standard FHIR [gender](https://hl7.org/fhir/R4/valueset-administrative-gender.html) is used. 

# Project Status
This project is in the alpha stage. However, if you are interested in getting it to run, please don't hesitate to reach out or submit an issue. 

# Requirements
This requires the python library, [NCPI-FHIR-Client](https://github.com/NIH-NCPI/ncpi-fhir-client)

# Constructing a fhir_hosts file
TBD

Feel free to reach out to me for directions on setting this up. The system supports basic password authentication, google healthcare via either service token or open auth 2 as well as the Kids First cookie authentication scheme. 

# Source and Destination Hosts
You are able to choose either a source host (-s, --source-env) as well as an optional destination host (-d, --dest-env), both of which must be defined in the fhir_hosts file. 