# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class PostSolver.
"""

from abc import ABC, abstractmethod
from importlib import import_module
from scr.logic.errors import SolverError
from scr.logic.circuit import Circuit
from typing import Dict
import logging as log


class PostSolver (ABC):
    @staticmethod
    def build(postsolver_name: str) -> 'PostSolver':
        """
        :raise SolverError: if the postsolver is not found.
        """
        # Dynamic importing modules
        try:
            cmp = import_module('scr.logic.solvers.postsolvers.' + postsolver_name)
        except ImportError:
            msg = f"Postsolver {postsolver_name} is not found."
            log.error(msg)
            raise SolverError(msg)
        # Only capitalize the first letter
        class_name = postsolver_name.replace(postsolver_name[0], postsolver_name[0].upper(), 1)
        class_ = getattr(cmp, class_name)
        return class_()

    @abstractmethod
    def post_solve(self, circuit: Circuit) -> Dict:
        """Calculate the solution for all the system.
        Calculated all desired properties, like thermodynamic properties of the nodes, the the basic and the auxiliary
        properties or the change of the units of the results. Is the information saved as solution in SolutionResults.
        """
        pass
