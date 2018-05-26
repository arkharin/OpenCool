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
import logging as log
import platform as plat
import pkg_resources


def configure_logs(log_level=log.DEBUG):
    # https://docs.python.org/3.6/howto/logging.html#logging-basic-tutorial
    # https://stackoverflow.com/questions/10973362/python-logging-function-name-file-name-line-number-using-a-single-file

    # FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
    # FORMAT = '%(levelname)s:%(message)s'
    FORMAT = '%(levelname)s:%(filename)s in line %(lineno)s (%(funcName)s):%(message)s'

    log.basicConfig(format=FORMAT, level=log_level)


# Logs for the program:
configure_logs()

# General information about system and OpenCool.

log.debug(f"Operating system: {plat.system()}")
log.debug(f"Platform: {plat.platform()}")
log.debug(f"Python version: {plat.python_version()}")
log.debug(f"CoolProp version: {pkg_resources.get_distribution('CoolProp').version}")
log.debug(f"Numpy version: {pkg_resources.get_distribution('Numpy').version}")
log.debug(f"Scipy version: {pkg_resources.get_distribution('Scipy').version}")


def _load_plugins_from_directory(dir_, use_working_directory_as_reference=True):
    base_dir = Path(dir_)
    if not base_dir.is_dir():
        raise ValueError
    cwd = Path(os.getcwd()) if use_working_directory_as_reference else base_dir

    for module_path in list(base_dir.glob('**/*.py')):
        # Avoid importing __init__.py
        if module_path.name != '__init__.py' and not module_path.match(cmp2.__file__):
            module_name = module_path.relative_to(cwd)
            module_name = module_name.with_suffix("")
            module_name = str(module_name)
            module_name = module_name.replace(os.sep, '.')
            import_module(module_name)
            log.debug(f"Plugin: {module_path} loaded successfully.")


# Load core plugins
log.info("Loading core plugins.")
core_plugins_directory = 'logic/components'
_load_plugins_from_directory(Path(os.getcwd()) / Path(core_plugins_directory))
log.info("Core plugins loaded.")

# Non-core plugins directory can be loaded too
log.info("Loading non-core plugins.")
plugins_directory = None  # '/foo/bar/'
if plugins_directory is not None:
    # Add plugins directory to sys path
    sys.path.insert(0, plugins_directory)
    _load_plugins_from_directory(plugins_directory, use_working_directory_as_reference=False)
log.info("Non-core plugins loaded.")


log.info("Loading system.")
#load_circuit = load('simple circuit complex presolver', 'OpenCool circuits')
#load_circuit = load('two stage circuit complex presolver', 'OpenCool circuits')
#load_circuit = load('simple circuit initial values', 'OpenCool circuits')
#load_circuit = load('two stage circuit initial values', 'OpenCool circuits')
load_circuit = load('test', 'OpenCool circuits')
log.debug("System file loaded successfully.")
#presolver = 'presolver_v01'  #Deprecated
presolver ='ComplexPresolver'
#presolver = 'OldComplexPresolver'
#solver = 'Root'  #Old simple circuit solver
solver = 'LeastSquares'

postsolver = 'postsolver_v01'

log.debug("Deserializing system.")
ser = circ.ACircuitSerializer()
circuit = ser.deserialize(load_circuit)
x0 = InitialValues.deserialize(load_circuit)
#x0 = None
log.debug("System deserialized successfully.")
log.debug("Building system")
circuit = circuit.build()
log.debug("System built successfully.")
log.info("System loaded successfully.")
log.info("Solving system.")
solver = Solver(circuit, presolver, solver, postsolver, x0)
solution = solver.solve()
log.info("Solver ends.")
log.info(f"Is system solved?: {solution.is_solved()}")
log.debug(f"The error is:\n {solution.get_errors()}")
log.debug(f"The maximum error is: {solution.get_maximum_error()}")

log.info("Saving system.")
log.debug("Serializing system.")
circuit_serialized = ser.serialize(circuit)
inital_values_serialized = x0.serialize()
solution_serialized = solution.serialize()
log.debug("System serialized.")
log.debug("Saving serialized system.")
data_to_save = {**circuit_serialized, **solution_serialized, **inital_values_serialized}

#save(data_to_save, 'simple circuit complex presolver', 'OpenCool circuits')
#save(data_to_save, 'one compressor-two evaporators complex presolver solved', 'OpenCool circuits')
#save(circuit_serialized, 'test', 'OpenCool circuits')
# save(solution_serialized, 'test', 'OpenCool circuits')
#save(data_to_save, 'simple circuit initial values solved', 'OpenCool circuits')
#save(data_to_save, 'two stage circuit initial values solved', 'OpenCool circuits')

# TODO hay TODO en el circuito!!
save(data_to_save, 'test', 'OpenCool circuits')
log.info("System saved.")
log.info("Program end.")

