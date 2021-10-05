import os
from setuptools import setup, find_packages

from summvar import __version__

root_dir = os.path.dirname(os.path.abspath(__file__))
req_file = os.path.join(root_dir, "requirements.txt")
with open(req_file) as f:
    requirements = f.read().splitlines()

setup(
    name="summarize-vars",
    version=__version__,
    description=f"FHIR Variable Summaries-Posthoc",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    scripts=["scripts/summarize_group.py"],
)
