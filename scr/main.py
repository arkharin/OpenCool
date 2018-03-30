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
from scr.logic.initial_values import InitialValues


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




#load_circuit = load('simple circuit complex presolver', 'OpenCool circuits')
#load_circuit = load('two stage circuit complex presolver', 'OpenCool circuits')
#load_circuit = load('simple circuit initial values', 'OpenCool circuits')
#load_circuit = load('two stage circuit initial values', 'OpenCool circuits')
load_circuit = load('test', 'OpenCool circuits')


#presolver = 'presolver_v01'  #Deprecated
presolver ='ComplexPresolver'
#presolver = 'OldComplexPresolver'
#solver = 'Root'  #Old simple circuit solver
solver = 'LeastSquares'

postsolver = 'postsolver_v01'


ser = circ.ACircuitSerializer()
circuit = ser.deserialize(load_circuit)
x0 = InitialValues.deserialize(load_circuit)
#x0 = None
print("circuit deserilize succesfully")
circuit = circuit.build()
solver = Solver(circuit, presolver, solver, postsolver, x0)
solution = solver.solve()
print('Is circuit solved? %s' % solution.is_solved())
print('The error is:\n')
print(solution.get_errors())
print('The maximum error is: %f' % solution.get_maximum_error())
print()
#print('The circuit solve is:\n')
#print(solution.get_all_circuits)

circuit_serialized = ser.serialize(circuit)
inital_values_serialized = x0.serialize()
solution_serialized = solution.serialize()
data_to_save = {**circuit_serialized, **solution_serialized, **inital_values_serialized}

#save(data_to_save, 'simple circuit complex presolver', 'OpenCool circuits')
#save(data_to_save, 'one compressor-two evaporators complex presolver solved', 'OpenCool circuits')
#save(circuit_serialized, 'test', 'OpenCool circuits')
# save(solution_serialized, 'test', 'OpenCool circuits')
#save(data_to_save, 'simple circuit initial values solved', 'OpenCool circuits')
#save(data_to_save, 'two stage circuit initial values solved', 'OpenCool circuits')

# TODO hay TODO en el circuito!!
save(data_to_save, 'test', 'OpenCool circuits')

print('end')

