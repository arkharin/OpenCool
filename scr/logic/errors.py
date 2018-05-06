# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Return error find in the program
"""


class TypeValueError(TypeError):
    pass


class ValuePropertyError(ValueError):
    pass

# TODO es el solver? el presolver? postSolver? Separar en Solver, Post, PreSolver error.
# TODO Este justamente se utiliza en el circuito, al construirse. Buscar otro nombre.
class CalculationError (RuntimeError):
    pass


class IdDuplicatedError(RuntimeError):
    pass


class TypeComponentError(TypeError):
    pass


class PropertyNameError(NameError):
    pass


class PropertyValueError(RuntimeError):
    pass


class BuildError(RuntimeError):
    pass


class DeserializerError(RuntimeError):
    pass


class PreSolverError(RuntimeError):
    pass


class SolverError(RuntimeError):
    pass


class PostSolverError(RuntimeError):
    pass


class InfoFactoryError(ValueError):
    pass


class InitialValuesError(RuntimeError):
    pass


class NodeError(RuntimeError):
    pass


class ComponentError(RuntimeError):
    pass


class InfoError(RuntimeError):
    pass


class ComponentDecoratorError(RuntimeError):
    pass
