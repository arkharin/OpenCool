# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the HEOS CoolProp backend for node.
"""

from scr.logic.nodes.node import Node


class CoolPropHeos(Node):

    def __init__(self, id_, components_id, refrigerant_object):
        super().__init__(id_, components_id, refrigerant_object)

    def get_type_property_base_1(self):
        return self.TEMPERATURE

    def get_type_property_base_2(self):
        return self.DENSITY

    def get_value_property_base_1(self):
        return self.temperature()

    def get_value_property_base_2(self):
        return self.density()

    def are_base_properties_init(self):
        if self._temperature is None and self._density is None:
            return False
        else:
            return True

    def _set_value_property_base_1(self, property_type_1, property_1, property_type_2, property_2):
        ref = self.get_refrigerant()
        self._temperature = ref.T(property_type_1, property_1, property_type_2, property_2)

    def _set_value_property_base_2(self, property_type_1, property_1, property_type_2, property_2):
        ref = self.get_refrigerant()
        self._density = ref.d(property_type_1, property_1, property_type_2, property_2)

    def get_limits_property_base_1(self):
        n_info = self.get_node_info()
        return n_info.get_property_limit(n_info.TEMPERATURE)

    def get_limits_property_base_2(self):
        n_info = self.get_node_info()
        return n_info.get_property_limit(n_info.DENSITY)


