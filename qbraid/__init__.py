# Copyright (C) 2023 qBraid
#
# This file is part of the qBraid-SDK
#
# The qBraid-SDK is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the qBraid-SDK, as per Section 15 of the GPL v3.

"""
This top level module contains the main qBraid public functionality.

.. currentmodule:: qbraid

Functions
----------

.. autosummary::
   :toctree: ../stubs/

   about
   get_devices
   refresh_devices
   get_jobs


Classes
--------

.. autosummary::
   :toctree: ../stubs/

   LazyLoader


Exceptions
-----------

.. autosummary::
   :toctree: ../stubs/

   QbraidError

"""
import sys

from . import _warnings
from ._about import about
from ._import import LazyLoader
from ._version import __version__
from .exceptions import QbraidError
from .get_devices import get_devices, refresh_devices
from .get_jobs import get_jobs

# TODO: Lazy loads break docs build, so for now, only loading if sphinx is not installed. However,
# this should instead be implemented as skip in sphinx config or in skip_member() in conf.py.
if "sphinx" not in sys.modules:
    # lazy load sub-modules
    compiler = LazyLoader("qbraid.compiler", globals())
    interface = LazyLoader("qbraid.interface", globals())
    programs = LazyLoader("qbraid.programs", globals())
    providers = LazyLoader("qbraid.providers", globals())
    transpiler = LazyLoader("qbraid.transpiler", globals())
    visualization = LazyLoader("qbraid.visualization", globals())
