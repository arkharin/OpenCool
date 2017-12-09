# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Solver using least squares algorithm that allows specify bound limits for the independent variables with a good
performance.

There are a lots of solver algorithms in SciPy. These can be classified in optimization and root finding.

Root finding algorithms find the roots of a function (can be a system of functions). The general API for
multidimensional functions is called root. The main problem with these solvers is that the user can't specify a
bound limits for the independent variables. This can lead to fall outside of the refrigerant library limits.

Optimization solver supports specify bound limits for the independent variables. The major drawback is the
performance cost. The main API for local optimization (local minimum)is called minimize. Least squares algorithm
allows specify bound limits with a good performance.

Be cautious that the Root finding algorithms and most of the Optimization solver are local finding methods,
no global and thermodynamics circuits have more than one minimum.

More information in https://docs.scipy.org/doc/scipy/reference/optimize.html

Examples of other algorithms:
Root:
      root(self._get_equations_error, ndarray_initial_conditions, args=circuit)

Minimize: the function to optimize return a one value (for example the square error) and _get_equations_error must
          be adapted.
          Bounds are a list of tupples with a pair of values (min and max)
          bnds = [(Min value 1, Max value 1), (Min value 2, Max value 2), ...]

      minimize(self._get_equations_error, ndarray_initial_conditions, args=circuit, bounds=bnds)

Bashinhopping: a global minimizer. Call several times minimize to found minimums. For print the minimize value
               use: print_fun = lambda x, f, accepted: print("at minimum %.4f accepted %d" % (f, int(accepted)))
               To pass the argument to minimizer: minimizer_kwargs = {"args": circuit, "bounds": bnds}
               Use the same function than minimize.

      basinhopping(self._get_equations_error, ndarray_initial_conditions, minimizer_kwargs= minimizer_kwargs,
                      callback=print_fun)

"""

import numpy as np
from scipy.optimize import least_squares
from scr.logic.solvers.solvers_algorithm.solver_algorithm import Solver_algorithm
from scr.logic.nodes.node import NodeInfoFactory, NodeInfo


class LeastSquares(Solver_algorithm):

    def __init__(self):
        super().__init__()
        self._solution = None

    def solve(self, circuit, initial_conditions, **kwargs):
        # Transform to numpy array.
        ndarray_initial_conditions = np.array(initial_conditions)
        # Calculated lower and upper bounds of the independent variables.
        node = circuit.get_node()
        lim_value_prop1 = node.get_limits_property_base_1()
        lim_value_prop2 = node.get_limits_property_base_2()
        lim_mass_flow = NodeInfoFactory.get(node).get_property_limit(NodeInfo.MASS_FLOW)
        nodes_quantity = len(circuit.get_nodes())
        flows_quantity = len(circuit.get_mass_flows())
        bnds = self._calc_bounds(lim_value_prop1, lim_value_prop2, nodes_quantity, lim_mass_flow, flows_quantity)
        # Call the least squares algorithm.
        self._solution = least_squares(self._get_equations_error, ndarray_initial_conditions, args=(circuit,), bounds=bnds)
        self._updated_circuit(self._solution['x'], circuit)
        return circuit

    def _calc_bounds(self, lim_value_prop1, lim_value_prop2, nodes_quantity, lim_mass_flow, flows_quantity):
        lim_value_prop1 = self._transform_property_limits(lim_value_prop1)
        lim_value_prop2 = self._transform_property_limits(lim_value_prop2)
        lim_mass_flow = self._transform_property_limits(lim_mass_flow)
        bnds1 = [lim_value_prop1[0], lim_value_prop2[0]] * nodes_quantity + [lim_mass_flow[0]] * flows_quantity
        bnds2 = [lim_value_prop1[1], lim_value_prop2[1]] * nodes_quantity + [lim_mass_flow[1]] * flows_quantity
        return bnds1, bnds2

    def _transform_property_limits(self, limits):
        lim = list(limits)
        if lim[0] is None:
            lim[0] = -np.inf
        if lim[1] is None:
            lim[1] = np.inf
        return lim

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