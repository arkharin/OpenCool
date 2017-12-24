# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Solver for simple circuit
"""

import numpy as np
from scipy.optimize import root
from scr.logic.solvers.solvers_algorithm.solver_algorithm import Solver_algorithm
from scr.logic.solvers.solver import SolutionResults as SR


class Root(Solver_algorithm):
    def __init__(self):
        super().__init__()
        self._solution = None

    def solve(self, circuit, initial_conditions, **kwargs):
        ndarray_initial_conditions = np.array(initial_conditions)
        self._solution = root(self._get_equations_error, ndarray_initial_conditions, args=circuit)
        return self._adapt_solution_to_solution_results()

    def _get_equations_error(self, x, circuit):
        self._updated_circuit(x, circuit)
        error = []
        components = circuit.get_components()
        for component in components:
            equations_results = components[component].eval_equations()
            for equation_result in equations_results:
                error.append(equation_result[0] - equation_result[1])
        return error

    def _adapt_solution_to_solution_results(self):
        solution_adapted = {SR.X: list(self._solution['x'])}
        solution_adapted[SR.SUCCESS] = self._solution['success']
        solution_adapted[SR.MESSAGE] = self._solution['message']
        solution_adapted[SR.RESIDUALS] = list(self._solution['fun'])
        min = abs(self._solution['fun'].min())
        max = abs(self._solution['fun'].max())
        if max > min:
            solution_adapted[SR.MAXRS] = max
        else:
            solution_adapted[SR.MAXRS] = min
        solution_adapted[SR.STATUS] = self._solution['status']
        solution_adapted[SR.SOLVER_SPECIFIC] = {'qtf': list(self._solution['qtf'])}
        solution_adapted[SR.SOLVER_SPECIFIC]['nfev'] = self._solution['nfev']
        solution_adapted[SR.SOLVER_SPECIFIC]['r'] = list(self._solution['r'])
        return solution_adapted
