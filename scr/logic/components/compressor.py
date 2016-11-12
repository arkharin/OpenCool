# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the Compressor component.
"""

from scr.logic.component import Component
from scr.logic.common import MAX_FLOAT_VALUE
from scr.logic.refrigerant import Refrigerant
from scr.logic.errors import PropertyNameError


class Compressor(Component):
    DISPLACEMENT_VOLUME = 'displacement_volume'
    ISENTROPIC_EFFICIENCY = 'isentropic_efficiency'
    POWER_CONSUMPTION = 'power_consumption'
    VOLUMETRIC_EFFICIENCY = 'volumetric_efficiency'

    basic_properties_allowed = {ISENTROPIC_EFFICIENCY: {'lower_limit': 0.0, 'upper_limit': 1.0},
                                POWER_CONSUMPTION: {'lower_limit': 0.0, 'upper_limit': MAX_FLOAT_VALUE}}

    optional_properties_allowed = {DISPLACEMENT_VOLUME: {'lower_limit': 0.0, 'upper_limit': MAX_FLOAT_VALUE},
                                   VOLUMETRIC_EFFICIENCY: {'lower_limit': 0.0, 'upper_limit': 1.0}}

    def __init__(self, name, identifier, inlet_nodes, outlet_nodes, basic_properties, optional_properties):
        super().__init__(name, identifier, self.COMPRESSOR, inlet_nodes, 1, outlet_nodes, 1, basic_properties,
                         self.basic_properties_allowed, optional_properties, self.optional_properties_allowed)

    def _calculated_result(self, key):
        if key is self.ISENTROPIC_EFFICIENCY:
            inlet_node = self.get_inlet_nodes()[0]
            h_in = inlet_node.enthalpy()
            s_in = inlet_node.entropy()
            outlet_node = self.get_outlet_nodes()[0]
            h_out = outlet_node.enthalpy()
            p_out = outlet_node.pressure()
            ref = outlet_node.get_refrigerant()
            h_is = ref.h(Refrigerant.PRESSURE, p_out, Refrigerant.ENTROPY, s_in)
            return (h_is-h_in)/(h_out-h_in)

        elif key is self.POWER_CONSUMPTION:
            inlet_node = self.get_inlet_nodes()[0]
            h_in = inlet_node.enthalpy()
            outlet_node = self.get_outlet_nodes()[0]
            h_out = outlet_node.enthalpy()
            mass_flow = h_out.mass_flow()
            return mass_flow * (h_out - h_in) / 1000.0

        elif key is self.VOLUMETRIC_EFFICIENCY:
            inlet_node = self.get_inlet_nodes()[0]
            mass_flow = inlet_node.mass_flow()
            density = inlet_node.density()
            volumetric_efficiency = self.get_optional_property(key)
            return mass_flow * density / volumetric_efficiency

        elif key is self.DISPLACEMENT_VOLUME:
            inlet_node = self.get_inlet_nodes()[0]
            mass_flow = inlet_node.mass_flow()
            density = inlet_node.density()
            displacement_volume = self.get_optional_property(key)
            return mass_flow * density / displacement_volume
        else:
            return PropertyNameError(
                    "Invalid property. %s  is not in %s]" % key)

    def _eval_equation_error(self, basic_property):
        return self._calculated_result(basic_property) - self.get_basic_property(basic_property)
