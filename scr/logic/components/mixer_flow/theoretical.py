# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the Mixer Flow component.
"""
from scr.logic.common import MAX_FLOAT_VALUE
from scr.logic.components.component import Component as cmp
from scr.logic.errors import PropertyNameError
from scr.logic.components.component import component, fundamental_property, basic_property, auxiliary_property
from scr.helpers.properties import NumericBoundary
from math import inf


def update_saved_data_to_last_version(orig_data, orig_version):
    # Here will be the code to update to update saved data to current format
    return orig_data


@component(['theoretical_mixer_flow'], 1, update_saved_data_to_last_version)
class Theoretical(cmp):
    PRESSURE_LOSE_1 = 'pressure lose inlet 1 - outlet'
    PRESSURE_LOSE_2 = 'pressure lose inlet 2 - outlet'

    basic_properties_allowed = {PRESSURE_LOSE_1: {cmp.LOWER_LIMIT: 0.0, cmp.UPPER_LIMIT: MAX_FLOAT_VALUE,
                                cmp.UNIT: 'kPa'}, PRESSURE_LOSE_2: {cmp.LOWER_LIMIT: 0.0,
                                cmp.UPPER_LIMIT: MAX_FLOAT_VALUE, cmp.UNIT: 'kPa'}}

    optional_properties_allowed = {}

    def __init__(self, data, circuit_nodes):
        super().__init__(data, circuit_nodes, 2, 1, self.basic_properties_allowed, self.optional_properties_allowed)

    @basic_property(pressure_lose_1=NumericBoundary(0, inf))
    def _eval_pressure_lose_1(self):
        id_inlet_nodes = self.get_id_inlet_nodes()
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        inlet_node_1 = self.get_inlet_node(id_inlet_nodes[0])
        p_in = inlet_node_1.pressure()
        p_out = outlet_node.pressure()
        return (p_in - p_out) / 1000.0

    @basic_property(pressure_lose_2= NumericBoundary(0, inf))
    def _eval_pressure_lose_2(self):
        id_inlet_nodes = self.get_id_inlet_nodes()
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        inlet_node_2 = self.get_inlet_node(id_inlet_nodes[1])
        p_in = inlet_node_2.pressure()
        p_out = outlet_node.pressure()
        return (p_in - p_out) / 1000.0

    def calculated_result(self, key):
        if key == self.PRESSURE_LOSE_1:
            return self._eval_pressure_lose_1()

        elif key == self.PRESSURE_LOSE_2:
            return self._eval_pressure_lose_2()

        else:
            raise PropertyNameError("Invalid property. %s  is not in %s]" % key)

    def _eval_basic_equation(self, key_basic_property):
        return [self.get_basic_property(key_basic_property), self.calculated_result(key_basic_property)]

    @fundamental_property()
    def _eval_intrinsic_equations(self):
        id_inlet_nodes = list(self.get_id_inlet_nodes())
        inlet_node_1 = self.get_inlet_node(id_inlet_nodes[0])
        inlet_node_2 = self.get_inlet_node(id_inlet_nodes[1])

        id_outlet_node = list(self.get_id_outlet_nodes())[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        h_in_1 = inlet_node_1.enthalpy()
        h_in_2 = inlet_node_2.enthalpy()
        h_out = outlet_node.enthalpy()
        mass_flow_in_1 = inlet_node_1.mass_flow()
        mass_flow_in_2 = inlet_node_2.mass_flow()
        mass_flow_out = outlet_node.mass_flow()

        return [[mass_flow_in_1 * h_in_1 + mass_flow_in_2 * h_in_2, mass_flow_out * h_out]]
