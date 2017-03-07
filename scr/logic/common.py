# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Common objects and functions used
"""

from sys import float_info, maxsize
from scr.logic.errors import TypeValueError, ValuePropertyError

# Maximum and minimum values of the system
MAX_INT_VALUE = maxsize
MIN_INT_VALUE = -maxsize
MAX_FLOAT_VALUE = float_info.max
MIN_FLOAT_VALUE = float_info.min


class Element:
    def __init__(self, name, identifier):
        check_type(name, str)
        self._name = name
        check_input_int(identifier, lower_limit=0)
        self._id = identifier

    def get_name(self):
        return self._name

    def get_id(self):
        return self._id


def check_input_float(value, lower_limit=MIN_FLOAT_VALUE, upper_limit=MAX_FLOAT_VALUE):
    if type(value) is float:
        if not lower_limit <= value <= upper_limit:
            raise ValuePropertyError(
                "Invalid value for the float. %s  must be between %s and %s]" % (value, lower_limit, upper_limit))
    else:
        raise TypeValueError("Bad type for the value. %s it is not float." % value)


def check_input_int(value, lower_limit=MIN_INT_VALUE, upper_limit=MAX_INT_VALUE):
    if type(value) is int:
        if not lower_limit <= value <= upper_limit:
            raise ValuePropertyError(
                "Invalid value for the int. %s  must be between %s and %s]" % (value, lower_limit, upper_limit))
    else:
        raise TypeValueError("Bad type for the value. %s it is not int." % value)


def check_input_str(value, value_allowed):
    if type(value) is str:
        if value != value_allowed:
            raise ValuePropertyError("Invalid string. %s is not %s" % (value, value_allowed))
    else:
        raise TypeValueError("Bad type for the value. %s it is not str." % value)


def check_keys_dictionary(input_dictionary, keys_allowed):
    check_type(input_dictionary, dict)
    for key in input_dictionary:
        if key not in keys_allowed:
            raise ValuePropertyError(
                "Invalid key for the dictionary. %s  is not in %s]" % keys_allowed)


def check_type(value, type_value):
    if type(value) is not type_value:
        raise TypeValueError("Bad type for the value. %s it is not %s." % (value, type_value))
