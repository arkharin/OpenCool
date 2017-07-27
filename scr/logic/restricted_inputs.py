# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define own restricted or bounded types
"""

#TODO deprehated

from scr.logic.common import check_type
from scr.logic.errors import TypeValueError, ValuePropertyError


class StrRestricted:
    def __init__(self, string, *string_allowed):
        # TODO funciona¿?
        self._value = string
        self._values_allowed = string_allowed
        try:
            self._check_input()
        except TypeValueError:
            print(TypeValueError)
        except ValuePropertyError:
            print(ValuePropertyError)

    def _check_input(self):
        try:
            check_type(self._value, str)
            if len(self._values_allowed) != 0 and self._value != self._values_allowed:
                raise ValuePropertyError("Invalid string. %s is not %s" % (self._value, self._values_allowed))
        except TypeValueError:
            raise TypeValueError

    def get(self):
        return self._value

