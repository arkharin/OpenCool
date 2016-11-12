# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import scr.logic.circuit as circ
from scr.logic.solver import solve_circuit


input_circuit = {'name': 'circuit 1', 'id': 1, 'refrigerant': 'R134A',
                 'nodes': [{'name': 'n1', 'id': 1}, {'name': 'n2', 'id': 2}, {'name': 'n3', 'id': 3},{'name': 'n4', 'id': 4}],
                 'components': [{'id': 1, 'name': 'compressor', 'type': 'compressor', 'inlet nodes': [1], 'outlet nodes': [2],
                                'basic properties': {'isentropic_efficiency': 0.7},
                                 'optional properties': {'volumetric_efficiency': 0.8}},
                                {'id': 2, 'name': 'condenser', 'type': 'condenser', 'inlet nodes': [2], 'outlet nodes': [3],
                                 'basic properties':{'saturation_temperature': 308.15, 'subcooling': 2.0, 'pressure_lose': 0.0},
                                 'optional properties': {}},
                                {'id': 3, 'name': 'expansion valve', 'type': 'expansion_valve', 'inlet nodes': [3],
                                 'outlet nodes': [4],
                                 'basic properties': {},
                                 'optional properties': {}},
                                {'id': 4, 'name': 'evaporator', 'type': 'evaporator', 'inlet nodes': [4],
                                 'outlet nodes': [1],
                                 'basic properties': {'saturation_temperature': 203.15, 'superheating': 5.0, 'cooling_power': 1.0, 'pressure_lose': 0.0},
                                 'optional properties': {}}
                                ]}

circuit = circ.Circuit(input_circuit)
error = solve_circuit(circuit)
print('The error is:\n')
print(error)
print('end')
