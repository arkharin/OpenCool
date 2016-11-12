# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the Expansion Valve component.
"""

from scr.logic.component import Component


class ExpansionValve(Component):

    basic_properties_allowed = {}

    optional_properties_allowed = {}

    def __init__(self, name, identifier, inlet_nodes, outlet_nodes, basic_properties, optional_properties):
        super().__init__(name, identifier, self.EXPANSION_VALVE, inlet_nodes, 1, outlet_nodes, 1, basic_properties,
                         self.basic_properties_allowed, optional_properties, self.optional_properties_allowed)

    def _calculated_result(self, key):
            return None

    def _eval_equation_error(self, basic_property):
        inlet_node = self.get_inlet_nodes()[0]
        h_in = inlet_node.enthalpy()
        outlet_node = self.get_outlet_nodes()[0]
        h_out = outlet_node.enthalpy()

        return (h_in - h_out) / 1000.0
