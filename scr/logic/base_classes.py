# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Base classes for the program
"""
from scr.logic.common import check_type, check_input_int
from scr.logic.errors import IdDuplicatedError


class Identifier:
    def __init__(self, *forbidden_id):
        self._next_id = 0
        self._forbidden_id = list(forbidden_id)

    @property
    def next(self):
        self._next_id = +1
        while self._next_id in self._forbidden_id:
            self._next_id = +1
        return self._next_id

    def add_forbidden_id(self, id_):
        if id_ in self._forbidden_id:
            raise IdDuplicatedError('This id %s is already in use', id_)
        else:
            self._forbidden_id.append(id_)


class Element:
    def __init__(self, name, identifier):
        self._name = name.get()
        check_input_int(identifier, lower_limit=0)
        self._id = identifier

    def get_name(self):
        return self._name

    def get_id(self):
        return self._id