# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define own restricted or bounded types
"""

from abc import ABC, abstractmethod
from math import inf
from scr.logic.common import check_type
from scr.logic.errors import TypeValueError, PropertyValueError


class Property(ABC):

    def __init__(self):
        self._value = None

    @abstractmethod
    def is_correct(self, value):
        pass

    def set(self, value):
        # Try to set a arbitrary value.
        if self.is_correct(value):
            self._value = value
        else:
            raise PropertyValueError("%s Value not allowable." % value)
    pass

    def get(self):
        """Return the saved value."""
        return self._value


class NumericProperty(Property):

    def __init__(self, lower_boundary=-inf, upper_boundary=inf, value=None, unit=None):
        super().__init__()
        self._lower_boundary = lower_boundary
        self._upper_boundary = upper_boundary
        self.set(value)
        self._unit = unit

    def is_correct(self, value):
        if value is not None:
            return self._lower_boundary <= value <= self._upper_boundary
        else:
            return True

    def get_unit(self):
        return self._unit


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
