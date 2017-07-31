# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class Solver_algorithm.
"""

from abc import ABC, abstractmethod
from importlib import import_module


class Solver_algorithm (ABC):
    def __init__(self):
        pass

    @staticmethod
    def build(solver_name):
        # Dynamic importing modules
        try:
            cmp = import_module('scr.logic.solvers.solvers_algorithm.' + solver_name)
        except ImportError:
            print('Error loading solver. Type: %s is not found', solver_name)
            exit(1)
        # Only capitalize the first letter
        class_name = solver_name.replace(solver_name[0], solver_name[0].upper(), 1)
        class_ = getattr(cmp, class_name)
        return class_()

    @abstractmethod
    def solve(self, circuit, initial_conditions, **kwargs):
        pass

    @abstractmethod
    def get_solution_error(self):
        pass

    @abstractmethod
    def is_solution_converged(self):
        pass

    @abstractmethod
    def exit_message(self):
        pass
