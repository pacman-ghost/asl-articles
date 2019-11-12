""" Application constants. """

import os

APP_NAME = "ASL Articles"
APP_VERSION = "v0.1" # nb: also update setup.py
APP_DESCRIPTION = "Searchable index of ASL articles."

BASE_DIR = os.path.abspath( os.path.join( os.path.split(__file__)[0], ".." ) )
