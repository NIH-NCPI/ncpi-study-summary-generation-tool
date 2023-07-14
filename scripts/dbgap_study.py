#!/usr/bin/env python

"""
We want to create study resources for these things we encounter, but we only 
have an id, so I guess we can scrape the actual data from dbgap. 
"""

import xmltodict
import requests

from summvar import system_prefix, system_url, study_id, create_dataset_study, create_study_group

import pdb

study_base = 'https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id='
study_details_base = "https://ftp.ncbi.nlm.nih.gov/dbgap/studies/phs001272/phs001272.v1.p1/GapExchange_phs001272.v1.p1.xml"

class InvalidStudyID(Exception):
    def __init__(self, study_id):
        self.id = study_id
        super().__init__(self.message())

    def message(self):
        return "No DbGAP study ID found matching {self.id}."

class DbGaPStudy:
    def __init__(self, phsid):
        global study_base, study_details_base
        self.accession_id = phsid
        self.data_unavailable = False
        # Stolen from brian walsh: 
        #https://github.com/anvilproject/client-apis/blob/master/pyAnVIL/anvil/dbgap/api.py
        self.url = f"{study_base}{phsid}"
        response = requests.get(self.url, allow_redirects=False)

        if response.status_code == 302:
            assert response.status_code == 302, response.status_code

            # the qualified accession includes some versioning details and is required
            # for getting access to the data we are looking for
            try:
                self.qualified_accession = response.headers['location'].split("=")[1]
            except:
                print(f"An issue has been encountered with the location: {response.headers['location']}")
                self.qualified_accession = []
                #pdb.set_trace()
            if len(self.qualified_accession) == 0:
                self.data_unavailable = True
                self.qualified_access = f"{self.accession_id}.??.??"
                configuration = {
                    "StudyNameEntrez": "Study is not currently available to the public",
                    "Description": "This study was not available from the public facing rest API",
                    "Attributions": "None available at this time",
                }
            else:
                details_url = f"https://ftp.ncbi.nlm.nih.gov/dbgap/studies/{phsid}/{self.qualified_accession}/GapExchange_{self.qualified_accession}.xml"
                response = requests.get(details_url)
                assert response.status_code == 200
                self.data = xmltodict.parse(response.text)

                configuration = self.data['GaPExchange']['Studies']['Study']['Configuration']
            # Not sure what the difference is between StudyNameEntrez and StudyNameReportPage
            self.title = configuration['StudyNameEntrez']
            self.description = configuration['Description']

            # This will take some parsing but should be useful when we are ready to
            # use it
            if 'Disease' in configuration:
                self.diseases = configuration['Disease']

            # Lists people such as principal investigator, etc. Again, will require 
            # some amount of parsing to make these useful
            self.attributions = configuration['Attributions']

            # has consent short/long name for each of the different types of 
            # consent
            if 'ConsentGroups' in configuration:
                self.consent_groups = configuration['ConsentGroups']
            else:
                self.consent_groups = ""
        else:
            raise InvalidStudyID(phsid)

    def study_group(self):
        return create_study_group(
            study=self.accession_id,
            dataset_name=None,
            member_count=0
        )

    def for_fhir(self, consortium):
        return create_dataset_study(consortium, 
                         self.accession_id, 
                         dataset_name=None, 
                         title=self.title, 
                         web_url=self.url, 
                         description=self.description)
        
        