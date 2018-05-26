# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Return errors found in the program.
"""


class CircuitError (RuntimeError):
    pass


class IdDuplicatedError(RuntimeError):
    pass


class PropertyValueError(RuntimeError):
    pass


class DeserializerError(RuntimeError):
    pass


class SolverError(RuntimeError):
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


class RefrigerantLibraryError(RuntimeError):
    pass
