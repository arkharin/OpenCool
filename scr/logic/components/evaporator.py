# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the Evaporator component.
"""

from scr.logic.component import Component
from scr.logic.common import MAX_FLOAT_VALUE
from scr.logic.errors import PropertyNameError


class Evaporator(Component):
    COOLING_POWER = 'cooling_power'
    PRESSURE_LOSE = 'pressure_lose'
    SATURATION_TEMPERATURE = 'saturation_temperature'
    SUPERHEATING = 'superheating'

    basic_properties_allowed = {SATURATION_TEMPERATURE: {'lower_limit': 0.0, 'upper_limit': MAX_FLOAT_VALUE},
                                COOLING_POWER: {'lower_limit': 0.0, 'upper_limit': MAX_FLOAT_VALUE},
                                SUPERHEATING: {'lower_limit': 0.0, 'upper_limit': MAX_FLOAT_VALUE},
                                PRESSURE_LOSE: {'lower_limit': 0.0, 'upper_limit': MAX_FLOAT_VALUE}}

    optional_properties_allowed = {}

    def __init__(self, name, identifier, inlet_nodes, outlet_nodes, basic_properties, optional_properties):
        super().__init__(name, identifier, self.EVAPORATOR, inlet_nodes, 1, outlet_nodes, 1, basic_properties,
                         self.basic_properties_allowed, optional_properties, self.optional_properties_allowed)

    def _calculated_result(self, key):
        if key is self.COOLING_POWER:
            inlet_node = self.get_inlet_nodes()[0]
            h_in = inlet_node.enthalpy()
            outlet_node = self.get_outlet_nodes()[0]
            h_out = outlet_node.enthalpy()
            mass_flow = outlet_node.mass_flow()
            return mass_flow*(h_out-h_in) / 1000.0

        elif key is self.SATURATION_TEMPERATURE:
            outlet_node = self.get_outlet_nodes()[0]
            p_out = outlet_node.pressure()
            ref = outlet_node.get_refrigerant()
            return ref.T_sat(p_out)

        elif key is self.SUPERHEATING:
            outlet_node = self.get_outlet_nodes()[0]
            t_out = outlet_node.temperature()
            p_out = outlet_node.pressure()
            ref = outlet_node.get_refrigerant()
            return t_out - ref.T_sat(p_out)

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
