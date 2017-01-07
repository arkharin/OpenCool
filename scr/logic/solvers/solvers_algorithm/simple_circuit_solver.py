# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Solver for simple circuit
"""

import numpy as np
from scipy.optimize import fsolve

from scr.logic.components.component import Component
from scr.logic.solvers.solvers_algorithm.solver_algorithm import Solver_algorithm

COMPRESSOR = Component.COMPRESSOR
CONDENSER = Component.CONDENSER
EVAPORATOR = Component.EVAPORATOR
EXPANSION_VALVE = Component.EXPANSION_VALVE

# TODO implementar clase solve? De esta manera pasaría todo junto el error, la solucion, y lo que sea.


class Simple_circuit_solver(Solver_algorithm):

    def __init__(self):
        super().__init__()
        self._error = None

    #TODO comprobar si llama al init de Solver o no.
    def solve(self, circuit, initial_conditions, **kwargs):
        ndarray_initial_conditions = np.array(initial_conditions)
        solution = fsolve(self._get_equations_error, ndarray_initial_conditions, factor=1.0,  args=circuit)
        self._calculate_nodes_solved(circuit)
        self._error = self._get_equations_error(solution, circuit)
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
            #error = components[component].eval_error(error)
        return error


    def _calculate_nodes_solved(self, circuit):
        # TODO input a circuit with their solution and return a dictionary with keys = identifier nodes and as value a
        # dictionary thermodynamic properties
        nodes = circuit.get_nodes()
        for node in nodes:
            node = nodes[node]
            node.update_node_values(node.get_type_property_base_1(), node.get_value_property_base_1(),
                                    node.get_type_property_base_2(), node.get_value_property_base_2())
            node.calculate_node()

    def get_solution_error(self):
        return self._error