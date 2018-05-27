# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define Solver class
"""

import scr.logic.solvers.presolvers.presolver as prslv
import scr.logic.solvers.solvers_algorithm.solver_algorithm as slv
import scr.logic.solvers.postsolvers.postsolver as psslv
from scr.logic.errors import SolverError
from scr.logic.circuit import Circuit
from typing import Optional, Dict, Callable, List
from scr.logic.initial_values import InitialValues
import logging as log


class Solver:

    def __init__(self, circuit: Circuit, presolver: str, solver: str, postsolver: str,
                 user_initial_values: Optional[InitialValues]=None) -> None:
        self._circuit = circuit
        self._solution = SolutionResults()
        self._solution[self._solution.SOLUTION_INFO] = {}
        self._solution[self._solution.SOLUTION_INFO][self._solution.PRESOLVER] = presolver
        self._solution[self._solution.SOLUTION_INFO][self._solution.SOLVER] = solver
        self._solution[self._solution.SOLUTION_INFO][self._solution.POSTSOLVER] = postsolver

        self._presolver = prslv.PreSolver.build(presolver)
        self._solver = slv.Solver_algorithm.build(solver)
        self._postsolver = psslv.PostSolver.build(postsolver)
        self._user_x0 = user_initial_values

    def solve(self) -> 'SolutionResults':
        """Solve the circuit."""
        try:
            initial_conditions = self._presolver.calculate_initial_conditions(self._circuit, self._user_x0)
        except SolverError as e:
            self._solution[self._solution.SOLUTION_INFO][self._solution.SUCCESS] = False
            self._solution[self._solution.SOLUTION_INFO][self._solution.MESSAGE] = e
        self._solution[self._solution.SOLUTION_INFO][self._solution.X0] = initial_conditions
        sol = self._solver.solve(self._circuit, initial_conditions)
        for k, v in sol.items():
            self._solution[self._solution.SOLUTION_INFO][k] = v
        self._updated_circuit()
        try:
            self._solution[self._solution.SOLUTION] = self._postsolver.post_solve(self._circuit)
        except SolverError as e:
            self._solution[self._solution.SOLUTION_INFO][self._solution.SUCCESS] = False
            self._solution[self._solution.SOLUTION_INFO][self._solution.MESSAGE] = e

        return self._solution

    def _updated_circuit(self) -> None:
        """Recalculated the circuit with the final values of the solver."""
        x = self._solution.get_final_values()
        nodes = self._circuit.get_nodes()
        i = 0
        for node in nodes:
            node = nodes[node]
            node.update_node_values(node.get_type_property_base_1(), x[i], node.get_type_property_base_2(), x[i + 1])
            i += 2
        self._circuit.update_mass_flows(x[i:len(x)])


class SolutionResults(dict):
    """
    Represents the solution result.

    This class have the following attributes:
        solution: (dict) have n-circuits with their id as key. For example: solution = { 'id circuit 1': circuit 1, ...}
            circuit: (dict) have the following keys:
                nodes: (dict) id of the nodes in the circuit. nodes: {'id node 1': results, 'id node 2': results, ...}
                components: (dict) id of the components in the circuit. components: {'id component 1': results,
                                                                                        'id component 2': results, ...}
                    results: (dict) the solution of the node or the component. The keys are the properties of the
                            NodeInfo or ComponentInfo. Have the value and the unit.
                        Node results: (dict) two items = {"value": (float) value, "unit": (str) unit}
                        Component results: (dict) = {"basic properties" : { "basic property 1": {"value": (float) value,
                                                    "unit": (str) unit}, ...}
                                                    "auxiliary properties": "auxiliary property 1":{
                                                    "value": (float) value, "unit": (str) unit}, ...},...}

        solution_info: (dict) Additional information about the solution. Have at least the following keys:
            presolver: (str) name of the presolver used.
            solver: (str) name of the solver used.
            postsolver: (str) name of the postsolver used.
            x0: (list) The initial values used in the solver for the independent variables.
            x: (list) The final values for the independent variables.
            success: (bool) Whether or not the solver exited successfully.
            message: (str) Description of the cause of the termination.
            residuals: (list) Vector of residuals at the solution.
            maxrs: (float) The maximum absoulte residual.
            status: (int) Termination status of the optimizer. Its value depends on the underlying solver.
                    Refer to message for details.
            solver specific: (dict) other information specific of the solver.
    """

    # Key names of the SolutionResults
    # Names inside solution
    SOLUTION = 'solution'
    CIRCUIT = 'circuit'
    NODES = 'nodes'
    COMPONENTS = 'components'
    BASIC_PROPERTIES = 'basic properties'
    AUXILIARY_PROPERTIES = 'auxiliary properties'
    RESULTS = 'results'
    VALUE = 'value'
    UNIT = 'unit'
    # Names inside solution info
    SOLUTION_INFO = 'solution info'
    PRESOLVER = 'presolver'
    SOLVER = 'solver'
    POSTSOLVER = 'postsolver'
    X0 = 'x0'
    X = 'x'
    SUCCESS = 'success'
    MESSAGE = 'message'
    RESIDUALS = 'residuals'
    MAXRS = 'maxrs'
    STATUS = 'status'
    SOLVER_SPECIFIC = 'solver specific'

    # Decorator definition.
    def is_init(func: Callable) -> Callable:
        """Decorator. Check if circuit is solved or not.

        :raise SolverError: if the circuit is not solved.
        """
        def func_wrapper(self, *args):
            try:
                if self.is_solved():
                    return func(self, *args)
                else:
                    msg = f"System is not solved."
                    log.error(msg)
                    raise SolverError(msg)
            except KeyError:
                msg = f"System is not solved."
                log.error(msg)
                raise SolverError(msg)
        return func_wrapper

    @is_init
    def get_node(self, node: int) -> Dict:
        return self.get_all_nodes().get(node)

    @is_init
    def get_nodes(self, circuit: int) -> Dict:
        """All nodes results of a circuit."""
        return self.get_circuit(circuit)[self.NODES]

    @is_init
    def get_all_nodes(self) -> Dict:
        """All nodes results of the system."""
        nds = {}
        for circuit in self.get_all_circuits():
            nds = {**nds, **self.get_nodes(circuit)}
        return nds

    @is_init
    def get_component(self, component: int) -> Dict:
        return self.get_all_components().get(component)

    @is_init
    def get_components(self, circuit: int) -> Dict:
        """"All components results of a circuit."""
        return self.get_circuit(circuit)[self.COMPONENTS]

    @is_init
    def get_all_components(self) -> Dict:
        """All components results of the system."""
        cmps = {}
        for circuit in self.get_all_circuits():
            cmps = {**cmps, **self.get_components(circuit)}
        return cmps

    @is_init
    def get_circuit(self, circuit: int) -> Dict:
        return self[self.SOLUTION][circuit]

    @is_init
    def get_all_circuits(self) -> Dict:
        """All circuits results"""
        return self[self.SOLUTION]

    @is_init
    def get_by_id(self, id_: int) -> Optional[Dict]:
        """Results of the id. Can be a circuit, a component or a node."""
        circ = self.get_all_circuits().get(id_)
        if circ is not None:
            return circ
        cmp = self.get_all_components().get(id_)
        if cmp is not None:
            return cmp
        nd = self.get_all_nodes().get(id_)
        if nd is not None:
            return nd
        return None

    @is_init
    def get_solution_info(self) -> Dict:
        """Additional information about the solution."""
        return self[self.SOLUTION_INFO]

    def is_solved(self) -> bool:
        # Can't be called get_solution_info because it will be recursive.
        return self[self.SOLUTION_INFO][self.SUCCESS]

    @is_init
    def solver_status(self) -> int:
        """Termination status of the optimizer, depends on the underlying solver. Refer to message for details."""
        return self.get_solution_info()[self.STATUS]

    @is_init
    def get_initial_values(self) -> List:
        """The initial values used in the solver for the independent variables."""
        return self.get_solution_info()[self.X0]

    @is_init
    def get_final_values(self) -> List:
        """The final values for the independent variables."""
        return self.get_solution_info()[self.X]

    @is_init
    def get_message_termination(self) -> str:
        """Description of the cause of the termination."""
        return self.get_solution_info()[self.MESSAGE]

    @is_init
    def get_errors(self) -> List:
        """Residuals of the solution."""
        return self.get_solution_info()[self.RESIDUALS]

    @is_init
    def get_maximum_error(self) -> float:
        """The maximum residual (error)."""
        return self.get_solution_info()[self.MAXRS]

    @is_init
    def get_solver_specific_info(self) -> Dict:
        return self.get_solution_info()[self.SOLVER_SPECIFIC]

    @is_init
    def get_presolver(self) -> str:
        return self.get_solution_info()[self.PRESOLVER]

    @is_init
    def get_solver(self) -> str:
        return self.get_solution_info()[self.SOLVER]

    @is_init
    def get_postsolver(self) -> str:
        return self.get_solution_info()[self.POSTSOLVER]

    def serialize(self) -> 'SolutionResults':
        return self

    def deserialize(self, results_file: Dict) -> Dict:
        return results_file
