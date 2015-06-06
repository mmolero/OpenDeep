"""
Code used throughout the entire OpenDeep package.
"""
from __future__ import division, absolute_import, print_function

# get the package version number from a single location
from . import version
__version__ = version.__version__

# internal imports for easy package structure
from . import data
from . import log
from . import data
from . import models
from . import monitor
from . import optimization
from . import utils

# so we can get `from opendeep import function, grad, sharedX,` etc.
from .utils.constructors import *