""" Setup the package.

    Install this module in development mode to get the tests to work:
      pip install --editable .[dev]
"""

import os
from setuptools import setup, find_packages

# ---------------------------------------------------------------------

# NOTE: We break the requirements out into separate files so that we can load them early
# into a Docker image, where they can be cached, instead of having to re-install them every time.

def parse_requirements( fname ):
    """Parse a requirements file."""
    lines = []
    fname = os.path.join( os.path.split(__file__)[0], fname )
    for line in open(fname,"r"):
        line = line.strip()
        if line == "" or line.startswith("#"):
            continue
        lines.append( line )
    return lines

# ---------------------------------------------------------------------

setup(
    name = "asl-articles",
    version = "1.0", # nb: also update constants.py
    description = "Searchable index of ASL articles.",
    license = "AGPLv3",
    packages = find_packages(),
    install_requires = parse_requirements( "requirements.txt" ),
    extras_require = {
        "dev": parse_requirements( "requirements-dev.txt" ),
    },
    include_package_data = True,
)
