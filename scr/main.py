# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import scr.logic.circuit as circ
from scr.logic.solvers.solver import Solver
from scr.model.model import load, save
from importlib import import_module
import scr.logic.components.component as cmp2
import os
import sys
from pathlib import Path


def _load_plugins_from_directory(dir_, use_working_directory_as_reference=True):
    base_dir = Path(dir_)
    if not base_dir.is_dir():
        raise ValueError
    cwd = Path(os.getcwd()) if use_working_directory_as_reference else base_dir

    for module_path in list(base_dir.glob('**/*.py')):
        print(module_path)
        # Avoid importing __init__.py
        if module_path.name != '__init__.py' and not module_path.match(cmp2.__file__):
            print(module_path)
            module_name = module_path.relative_to(cwd)
            module_name = module_name.with_suffix("")
            module_name= str(module_name)
            module_name = module_name.replace(os.sep, '.')
            import_module(module_name)

# Load core plugins
core_plugins_directory = 'logic/components'
_load_plugins_from_directory(Path(os.getcwd()) / Path(core_plugins_directory))

# Non-core plugins directory can be loaded too
plugins_directory = None  # '/foo/bar/'
if plugins_directory is not None:
    # Add plugins directory to sys path
    sys.path.insert(0, plugins_directory)
    _load_plugins_from_directory(plugins_directory, use_working_directory_as_reference=False)

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

#save(input_circuit, 'input_circuit', 'OpenCool circuits')
#load_circuit = load('input_circuit builder_victor', 'OpenCool circuits')
#load_circuit = load('input_circuit builder', 'OpenCool circuits')

load_circuit = load('circuit_solved builder v2', 'OpenCool circuits')
ser = circ.ACircuitSerializer()
circuit = ser.deserialize(load_circuit)
print("circuit deserilize succesfully")
circuit = circuit.build()
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
save_circuit = ser.serialize(circuit_solved)
save(save_circuit, 'circuit_solved builder', 'OpenCool circuits')

print('end')

