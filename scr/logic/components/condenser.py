# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the Condenser component.
"""

from scr.logic.component import Component
from scr.logic.common import MAX_FLOAT_VALUE
from scr.logic.errors import PropertyNameError


class Condenser(Component):
    HEATING_POWER = 'heating_power'
    PRESSURE_LOSE = 'pressure_lose'
    SATURATION_TEMPERATURE = 'saturation_temperature'
    SUBCOOLING = 'subcooling'

    basic_properties_allowed = {SATURATION_TEMPERATURE: {'lower_limit': 0.0, 'upper_limit': MAX_FLOAT_VALUE},
                                HEATING_POWER: {'lower_limit': 0.0, 'upper_limit': MAX_FLOAT_VALUE},
                                SUBCOOLING: {'lower_limit': 0.0, 'upper_limit': MAX_FLOAT_VALUE},
                                PRESSURE_LOSE: {'lower_limit': 0.0, 'upper_limit': MAX_FLOAT_VALUE}}

    optional_properties_allowed = {}

    def __init__(self, name, identifier, inlet_nodes, outlet_nodes, basic_properties, optional_properties):
        super().__init__(name, identifier, self.CONDENSER, inlet_nodes, 1, outlet_nodes, 1, basic_properties,
                         self.basic_properties_allowed, optional_properties, self.optional_properties_allowed)

    def _calculated_result(self, key):
        if key is self.HEATING_POWER:
            inlet_node = self.get_inlet_nodes()[0]
            h_in = inlet_node.enthalpy()
            outlet_node = self.get_outlet_nodes()[0]
            h_out = outlet_node.enthalpy()
            mass_flow = outlet_node.mass_flow()
            return mass_flow*(h_in-h_out) / 1000.0

        elif key is self.SATURATION_TEMPERATURE:
            inlet_node = self.get_inlet_nodes()[0]
            p_in = inlet_node.pressure()
            ref = inlet_node.get_refrigerant()
            return ref.T_sat(p_in)

        elif key is self.SUBCOOLING:
            outlet_node = self.get_outlet_nodes()[0]
            t_out = outlet_node.temperature()
            p_out = outlet_node.pressure()
            ref = outlet_node.get_refrigerant()
            return ref.T_sat(p_out) - t_out

        elif key is self.PRESSURE_LOSE:
            inlet_node = self.get_inlet_nodes()[0]
            p_in = inlet_node.pressure()
            outlet_node = self.get_outlet_nodes()[0]
            p_out = outlet_node.pressure()
            return (p_in - p_out) / 1000.0
        else:
            raise PropertyNameError("Invalid property. %s  is not in %s]" % key)

    def _eval_equation_error(self, basic_property):
        return self._calculated_result(basic_property) - self.get_basic_property(basic_property)
