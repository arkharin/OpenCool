# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define Solver class
"""

import scr.logic.solvers.presolvers.presolver as prslv
import scr.logic.solvers.solvers_algorithm.solver_algorithm as slv
import scr.logic.solvers.postsolvers.postsolver as psslv


class Solver:
    NO_INIT = None

    def __init__(self, circuit, presolver, solver, postsolver):
        self._circuit = circuit
        self._circuit_solved = self.NO_INIT
        self._solution_error = self.NO_INIT

        self._presolver = prslv.PreSolver.build(presolver)
        self._solver = slv.Solver_algorithm.build(solver)
        self._postsolver = psslv.PostSolver.build(postsolver)

    def solve(self):
        circuit = self.get_circuit()
        initial_conditions = self._presolver.calculate_initial_conditions(circuit)
        self._circuit_solved = self._solver.solve(circuit, initial_conditions)
        self._solution_error = self._solver.get_solution_error()
        self._circuit_solved = self._postsolver.post_solve(self._circuit_solved)

    def get_circuit (self):
        return self._circuit

    def get_circuit_solved(self):
        return self._circuit_solved

    def get_solution_error(self):
        return self._solution_error

    def is_circuit_solved(self):
        if self.get_circuit_solved() is None:
            return False
        else:
            return True

