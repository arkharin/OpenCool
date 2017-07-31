# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Solver for simple circuit
"""

import numpy as np
from scipy.optimize import root
from scr.logic.components.component import Component
from scr.logic.solvers.solvers_algorithm.solver_algorithm import Solver_algorithm

COMPRESSOR = Component.COMPRESSOR
CONDENSER = Component.CONDENSER
EVAPORATOR = Component.EVAPORATOR
EXPANSION_VALVE = Component.EXPANSION_VALVE


class Simple_circuit_solver(Solver_algorithm):

    def __init__(self):
        super().__init__()
        self._solution = None

    def solve(self, circuit, initial_conditions, **kwargs):
        ndarray_initial_conditions = np.array(initial_conditions)
        self._solution = root(self._get_equations_error, ndarray_initial_conditions, args=circuit)
        return circuit

    def _get_equations_error(self, x, circuit):
        nodes = circuit.get_nodes()
        i = 0
        for node in nodes:
            node = nodes[node]
            node.update_node_values(node.get_type_property_base_1(), x[i], node.get_type_property_base_2(), x[i+1])
            i += 2
        circuit.update_mass_flows(x[i:len(x)])
        error = []
        components = circuit.get_components()
        for component in components:
            equations_results = components[component].eval_equations()
            for equation_result in equations_results:
                error.append(equation_result[0] - equation_result[1])
        return error

    def get_solution_error(self):
        return self._solution['fun']

    def is_solution_converged(self):
            return self._solution['success']

    def exit_message(self):
        return self._solution['message']