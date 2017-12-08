# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Solver for simple circuit
"""

import numpy as np
from scipy.optimize import root
from scr.logic.solvers.solvers_algorithm.solver_algorithm import Solver_algorithm


class Root(Solver_algorithm):
    def __init__(self):
        super().__init__()
        self._solution = None

    def solve(self, circuit, initial_conditions, **kwargs):
        ndarray_initial_conditions = np.array(initial_conditions)
        self._solution = root(self._get_equations_error, ndarray_initial_conditions, args=circuit)
        return circuit

    def _get_equations_error(self, x, circuit):
        self._updated_circuit(x, circuit)
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