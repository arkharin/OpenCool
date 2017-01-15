# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the Condenser component.
"""

from scr.logic.common import MAX_FLOAT_VALUE
from scr.logic.components.component import Component as cmp
from scr.logic.errors import PropertyNameError


class Theoretical(cmp):
    HEATING_POWER = 'heating_power'
    PRESSURE_LOSE = 'pressure_lose'
    SATURATION_TEMPERATURE = 'saturation_temperature'
    SUBCOOLING = 'subcooling'

    basic_properties_allowed = {SATURATION_TEMPERATURE: {cmp.LOWER_LIMIT: 0.0, cmp.UPPER_LIMIT: MAX_FLOAT_VALUE,
                                                         cmp.UNIT: 'K'},
                                HEATING_POWER: {cmp.LOWER_LIMIT: 0.0, cmp.UPPER_LIMIT: MAX_FLOAT_VALUE, cmp.UNIT: 'kW'},
                                SUBCOOLING: {cmp.LOWER_LIMIT: 0.0, cmp.UPPER_LIMIT: MAX_FLOAT_VALUE, cmp.UNIT: 'K'},
                                PRESSURE_LOSE: {cmp.LOWER_LIMIT: 0.0, cmp.UPPER_LIMIT: MAX_FLOAT_VALUE, cmp.UNIT: 'kPa'}
                                }

    optional_properties_allowed = {}

    def __init__(self, data, circuit_nodes):
        super().__init__(data, circuit_nodes, 1, 1, self.basic_properties_allowed, self.optional_properties_allowed)

    def _calculated_result(self, key):
        id_inlet_node = list(self.get_id_inlet_nodes())[0]
        inlet_node = self.get_inlet_node(id_inlet_node)
        id_outlet_node = list(self.get_id_outlet_nodes())[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        if key == self.HEATING_POWER:
            h_in = inlet_node.enthalpy()
            h_out = outlet_node.enthalpy()
            mass_flow = outlet_node.mass_flow()
            return mass_flow*(h_in-h_out) / 1000.0

        elif key == self.SATURATION_TEMPERATURE:
            p_in = inlet_node.pressure()
            ref = inlet_node.get_refrigerant()
            return ref.T_sat(p_in)

        elif key == self.SUBCOOLING:
            t_out = outlet_node.temperature()
            p_out = outlet_node.pressure()
            ref = outlet_node.get_refrigerant()
            return ref.T_sat(p_out) - t_out

        elif key == self.PRESSURE_LOSE:
            p_in = inlet_node.pressure()
            p_out = outlet_node.pressure()
            return (p_in - p_out) / 1000.0
        else:
            raise PropertyNameError("Invalid property. %s  is not in %s]" % key)

    def _eval_basic_equation(self, basic_property):
        return [self.get_basic_property(basic_property), self._calculated_result(basic_property)]

    def _eval_intrinsic_equations(self):
        return None
