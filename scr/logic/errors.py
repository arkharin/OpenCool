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


class CalculationError (RuntimeError):
    pass


class IdDuplicated(RuntimeError):
    pass


class TypeComponentError(TypeError):
    pass


class PropertyNameError(NameError):
    pass
