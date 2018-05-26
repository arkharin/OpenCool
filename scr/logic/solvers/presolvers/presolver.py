# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class Presolver.
"""


from abc import ABC, abstractmethod
from importlib import import_module
import logging as log
from scr.logic.errors import SolverError
from scr.logic.circuit import Circuit
from scr.logic.initial_values import InitialValues
from typing import List


class PreSolver (ABC):
    @staticmethod
    def build(presolver_name: str) -> 'PreSolver':
        """
        :raise SolverError: if the presolver is not found.
        """
        # Dynamic importing modules
        try:
            cmp = import_module('scr.logic.solvers.presolvers.' + presolver_name)
        except ImportError:
            msg = f"Presolver {presolver_name} is not found."
            log.error(msg)
            raise SolverError(msg)
        # Only capitalize the first letter
        class_name = presolver_name.replace(presolver_name[0], presolver_name[0].upper(), 1)
        class_ = getattr(cmp, class_name)
        return class_()

    @abstractmethod
    def calculate_initial_conditions(self, circuit: Circuit, user_initial_values: InitialValues =None) -> List[float]:
        """Calculate the initial conditions.

        All nodes are initialized with the pair of basic thermodynamic properties for node library and mass flows of the
        circuit.

        :raise SolverError.
        """
        pass
