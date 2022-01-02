""" This module is responsible for importing pyquarto correctly.  It
modifies the paths to find the _pyquarto.pyd as appropriate.  Use
"import import_pyquarto as pyquarto" instead of "import pyquarto".
"""

import sys
import os

# SWIG leaves pyquarto.py in the c/build directory.  MSVC leaves
# _pyquarto.pyd in c/build/RelWithDebInfo directory.  We need to
# both of these directories to sys.path so we can import these
# modules.

# Furthermore, it can't be a relative directory name on sys.path,
# it has to be an absolute directory name from the root (for some
# reason), so we use abs.path to fix that.
thisdir = os.path.abspath(os.path.dirname(__file__))

# Then we get the build dir and subbuild dir.
build_dir = os.path.normpath(os.path.join(thisdir, '..', 'c', 'build'))
assert(os.path.isdir(build_dir))

subbuild_dir = os.path.normpath(os.path.join(build_dir, 'RelWithDebInfo'))
assert(os.path.isdir(subbuild_dir))

sys.path.append(subbuild_dir)
sys.path.append(build_dir)

# Now that the paths are set up correctly, we can safely import
# pyquarto, which itself internally imports _pyquarto.pyd.
from pyquarto import *
