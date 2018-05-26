# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define own restricted or bounded types
"""

from abc import ABC, abstractmethod
from math import inf
from scr.logic.errors import PropertyValueError
from typing import Optional, List, Any, Union
import logging as log


class Property(ABC):

    def __init__(self):
        self._value = None

    @abstractmethod
    def is_correct(self, value: Any) -> bool:
        pass

    def set(self, value: Any) -> None:
        """Try to set a arbitrary value.

        :raise PropertyValueError: value it isn't allowable.
        """
        if self.is_correct(value):
            self._value = value
        else:
            msg = f"{value} is not allowable."
            log.warning(msg)
            raise PropertyValueError(msg)
    pass

    def get(self) -> Any:
        """Return the saved value."""
        return self._value


class NumericProperty(Property):

    def __init__(self, lower_boundary: Union[int, float] =-inf, upper_boundary: Union[int, float] =inf,
                 value: Optional[Union[int, float]] =None, unit: Optional[str] =None) -> None:
        super().__init__()
        self._lower_boundary = lower_boundary
        self._upper_boundary = upper_boundary
        if value is not None:
            self.set(value)
        self._unit = unit

    def is_correct(self, value: Any) -> bool:
        return self._lower_boundary <= value <= self._upper_boundary

    def get_unit(self):
        return self._unit

    def get_limits(self):
        return [self._lower_boundary, self._upper_boundary]


class StrRestricted(Property):
    """String restriction class.

    String must be one of string allowed.
    """
    def __init__(self, string: Optional[str]=None, strings_allowed: Optional[List[str]]= None):
        """
        :raise PropertyValueError
        """
        super().__init__()
        self._values_allowed = strings_allowed
        self.set(string)

    def is_correct(self, value: Any) -> bool:
        if type(value) is str:
            if self._values_allowed is None:
                return True
            else:
                return value in self._values_allowed
        else:
            return False
