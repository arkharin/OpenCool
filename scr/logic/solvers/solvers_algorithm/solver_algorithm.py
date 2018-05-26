# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class Solver_algorithm.
"""

from abc import ABC, abstractmethod
from importlib import import_module
import logging as log
from scr.logic.errors import SolverError
from scr.logic.circuit import Circuit
from typing import List, Dict


class Solver_algorithm (ABC):
    @staticmethod
    def build(solver_name: str) -> 'Solver_algorithm':
        """
        :raise SolverError: if the solver algorithm is not found.
        """
        # Dynamic importing modules
        try:
            cmp = import_module('scr.logic.solvers.solvers_algorithm.' + solver_name)
        except ImportError:
            msg = f"Solver {solver_name} is not found."
            log.error(msg)
            raise SolverError(msg)
        # Only capitalize the first letter
        class_name = solver_name.replace(solver_name[0], solver_name[0].upper(), 1)
        class_ = getattr(cmp, class_name)
        return class_()

    @abstractmethod
    def solve(self, circuit: Circuit, initial_conditions: List[float], **kwargs) -> Dict:
        """Solve the circuit.

        Return the items defined in SoltionResults: x, success, message, residuals, maxrs, status and solver specific.
        """
        pass

    # Shared functions between solvers algorithms.
    def _updated_circuit(self, x: List[float], circuit: Circuit) -> None:
        """Updated the circuit with the values of the independent variables."""
        nodes = circuit.get_nodes()
        i = 0
        for node in nodes:
            node = nodes[node]
            node.update_node_values(node.get_type_property_base_1(), x[i], node.get_type_property_base_2(), x[i + 1])
            i += 2
        circuit.update_mass_flows(x[i:len(x)])
