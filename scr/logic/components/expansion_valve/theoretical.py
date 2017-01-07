# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the Expansion Valve component.
"""

from scr.logic.components.component import Component


class Theoretical(Component):

    basic_properties_allowed = {}

    optional_properties_allowed = {}

    def __init__(self, data, circuit_nodes):
        super().__init__(data, circuit_nodes, 1, 1, self.basic_properties_allowed, self.optional_properties_allowed)

    def _calculated_result(self, key):
            return None

    def _eval_basic_equation(self, basic_property):
        return None

    def _eval_intrinsic_equations(self):
        id_inlet_node = list(self.get_id_inlet_nodes())[0]
        inlet_node = self.get_inlet_node(id_inlet_node)
        id_outlet_node = list(self.get_id_outlet_nodes())[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        h_in = inlet_node.enthalpy()
        h_out = outlet_node.enthalpy()

        return [h_in / 1000.0, h_out / 1000.0]