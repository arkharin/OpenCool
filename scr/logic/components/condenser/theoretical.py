# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the Condenser component.
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

@component(['theoretical_condenser'], 1, update_saved_data_to_last_version)
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

    def __init__(self, name, id_, component_type, inlet_nodes_id, outlet_nodes_id, component_data):
        super().__init__(name, id_, component_type, inlet_nodes_id, outlet_nodes_id, component_data, 1, 1, self.basic_properties_allowed, self.optional_properties_allowed)

    ### Fundamental properties equations ###

    ### Basic properties equations ###
    # Name must be only one word

    @basic_property(heating_power=NumericBoundary(0, inf))
    def _eval_heating_power(self):
        id_inlet_node = self.get_id_inlet_nodes()[0]
        inlet_node = self.get_inlet_node(id_inlet_node)
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)
        h_in = inlet_node.enthalpy()
        h_out = outlet_node.enthalpy()
        mass_flow = outlet_node.mass_flow()
        return mass_flow * (h_in - h_out) / 1000.0

    @basic_property(saturation_temperature=NumericBoundary(0, inf))
    def _eval_saturation_temperature(self):
        id_inlet_node = self.get_id_inlet_nodes()[0]
        inlet_node = self.get_inlet_node(id_inlet_node)

        p_in = inlet_node.pressure()
        ref = inlet_node.get_refrigerant()
        return ref.T_sat(p_in)

    @basic_property(subcooling=NumericBoundary(0, inf))
    def _eval_subcooling(self):
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        t_out = outlet_node.temperature()
        p_out = outlet_node.pressure()
        ref = outlet_node.get_refrigerant()
        return ref.T_sat(p_out) - t_out

    @basic_property(pressure_lose=NumericBoundary(0, inf))
    def _eval_pressure_loss(self):
        id_inlet_node = self.get_id_inlet_nodes()[0]
        inlet_node = self.get_inlet_node(id_inlet_node)
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        p_in = inlet_node.pressure()
        p_out = outlet_node.pressure()
        return (p_in - p_out) / 1000.0

    def calculated_result(self, key):
        if key == self.HEATING_POWER:
            return self._eval_heating_power()

        elif key == self.SATURATION_TEMPERATURE:
            return self._eval_saturation_temperature()

        elif key == self.SUBCOOLING:
            return self._eval_subcooling()

        elif key == self.PRESSURE_LOSE:
            return self._eval_pressure_loss()
        else:
            raise PropertyNameError("Invalid property. %s  is not in %s]" % key)

    def _eval_basic_equation(self, key_basic_property):
        return [self.get_basic_property(key_basic_property), self.calculated_result(key_basic_property)]

    def _eval_intrinsic_equations(self):
        return None

