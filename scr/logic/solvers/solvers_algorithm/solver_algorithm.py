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
        # Return a dict with the items follwing items defined in SoltionResults: x, success, message, residuals, maxrs,
        # status, solver specific
        pass

    # Shared functions between solvers algorithms.
    def _updated_circuit(self, x, circuit):
        nodes = circuit.get_nodes()
        i = 0
        for node in nodes:
            node = nodes[node]
            node.update_node_values(node.get_type_property_base_1(), x[i], node.get_type_property_base_2(), x[i + 1])
            i += 2
        circuit.update_mass_flows(x[i:len(x)])
