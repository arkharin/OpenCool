# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define own restricted or bounded types
"""

from abc import ABC, abstractmethod
from math import inf
from scr.logic.common import check_type
from scr.logic.errors import TypeValueError, ValuePropertyError

# FIXME los métodos de set deberían lanzar un warning de porque no se ha podido guardar el valor


class Property(ABC):

    def __init__(self):
        self._value = None

    @abstractmethod
    def is_correct(self, value):
        pass

    def set(self, value):
        """Try to set the value. 
        
        Return true if the setted value is correct y is setted.
        Return false if the value is incorrect and wasn't saved"""
        if self.is_correct(value):
            self._value = value
            return True
        return False

    def get(self):
        """Return the saved value."""
        return self._value


class NumericBoundary(Property):

    def __init__(self, lower_boundary=-inf, upper_boundary=inf, value=None):
        super().__init__()
        self._lower_boundary = lower_boundary
        self._upper_boundary = upper_boundary
        self.set(value)

    def is_correct(self, value):
        if self._value is not None:
            return self._lower_boundary < value < self._upper_boundary
        else:
            return True


class StrRestricted(Property):
    def __init__(self, string=None, *string_allowed):
        super().__init__()
        self._values_allowed = string_allowed
        self.set(string)

    def is_correct(self, value):
        if self._value is not None:
            try:
                check_type(self._value, str)
                return len(self._values_allowed) != 0 and self._value != self._values_allowed
            except TypeValueError:
                return False
        else:
            return True
