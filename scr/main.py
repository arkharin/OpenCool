# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import scr.logic.circuit as circ
from scr.logic.solvers.solver import Solver

input_circuit = {'name': 'circuit 1', 'id': 1, 'refrigerant': 'R134A', 'refrigerant_library': 'CoolPropHeos',
                 'nodes': [{'name': 'n1', 'id': 1}, {'name': 'n2', 'id': 2}, {'name': 'n3', 'id': 3},{'name': 'n4', 'id': 4}],
                 'components': [{'id': 1, 'name': 'compressor', 'type': 'compressor.theoretical', 'inlet nodes': [1], 'outlet nodes': [2],
                                'basic properties': {'isentropic_efficiency': 0.7},
                                 'optional properties': {'volumetric_efficiency': 0.8}},
                                {'id': 2, 'name': 'condenser', 'type': 'condenser.theoretical', 'inlet nodes': [2], 'outlet nodes': [3],
                                 'basic properties':{'saturation_temperature': 308.15, 'subcooling': 2.0, 'pressure_lose': 0.0},
                                 'optional properties': {}},
                                {'id': 3, 'name': 'expansion valve', 'type': 'expansion_valve.theoretical', 'inlet nodes': [3],
                                 'outlet nodes': [4],
                                 'basic properties': {},
                                 'optional properties': {}},
                                {'id': 4, 'name': 'evaporator', 'type': 'evaporator.theoretical', 'inlet nodes': [4],
                                 'outlet nodes': [1],
                                 'basic properties': {'saturation_temperature': 203.15, 'superheating': 5.0, 'cooling_power': 1.0, 'pressure_lose': 0.0},
                                 'optional properties': {}}
                                ]}

circuit = circ.Circuit(input_circuit)

presolver = 'presolver_v01'
solver = 'simple_circuit_solver'
postsolver = 'postsolver_v01'
solver = Solver(circuit, presolver, solver, postsolver)
solver.solve()
circuit_solved = solver.get_circuit_solved()
is_solved = solver.is_circuit_solved()
error = solver.get_solution_error()
exit_message = solver._exit_message_solver_algorithm
print('Is circuit solved? %s' %is_solved)
print(exit_message)
print('The error is:\n')
print(error)
print()
print('The circuit solve is:\n')
print(circuit_solved)
print('end')
