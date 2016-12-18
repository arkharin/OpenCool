# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class Presolver.
"""


from abc import ABC, abstractmethod
from importlib import import_module


class PreSolver (ABC):
    def __init__(self):
        pass

    @staticmethod
    def build(presolver_name):
        # Dynamic importing modules
        try:
            cmp = import_module('scr.logic.solvers.presolvers.' + presolver_name)
        except ImportError:
            print('Error loading presolver. Type: %s is not found', presolver_name)
            exit(1)
        # Only capitalize the first letter
        class_name = presolver_name.replace(presolver_name[0], presolver_name[0].upper(), 1)
        class_ = getattr(cmp, class_name)
        return class_()

    @abstractmethod
    def calculate_initial_conditions(self, circuit):
        pass
