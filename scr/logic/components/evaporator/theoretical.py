# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the Evaporator component.
"""

from scr.logic.common import MAX_FLOAT_VALUE
from scr.logic.components.component import Component as cmp
from scr.logic.errors import PropertyNameError
from scr.logic.components.component import component, fundamental_property, basic_property, auxiliary_property
from scr.helpers.properties import NumericProperty
from math import inf

def update_saved_data_to_last_version(orig_data, orig_version):
    # Here will be the code to update to update saved data to current format
    return orig_data


@component('theoretical_evaporator', cmp.EVAPORATOR, 1, update_saved_data_to_last_version)
class Theoretical(cmp):
    COOLING_POWER = 'cooling_power'
    PRESSURE_LOSE = 'pressure_lose'
    SATURATION_TEMPERATURE = 'saturation_temperature'
    SUPERHEATING = 'superheating'

    def __init__(self, name, id_, inlet_nodes_id, outlet_nodes_id, component_data):
        super().__init__(name, id_, inlet_nodes_id, outlet_nodes_id, component_data)

    @basic_property(cooling_power=NumericProperty(0, inf, unit='kW'))
    def _eval_cooling_power(self):
        id_inlet_node = self.get_id_inlet_nodes()[0]
        inlet_node = self.get_inlet_node(id_inlet_node)
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        h_in = inlet_node.enthalpy()
        h_out = outlet_node.enthalpy()
        mass_flow = outlet_node.mass_flow()
        return mass_flow * (h_out - h_in) / 1000.0

    @basic_property(saturation_temperature=NumericProperty(0, inf, unit='K'))
    def _eval_saturation_temperature(self):
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        p_out = outlet_node.pressure()
        ref = outlet_node.get_refrigerant()
        return ref.T_sat(p_out)

    @basic_property(superheating=NumericProperty(0, inf, unit='K'))
    def _eval_superheating(self):
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        t_out = outlet_node.temperature()
        p_out = outlet_node.pressure()
        ref = outlet_node.get_refrigerant()
        return t_out - ref.T_sat(p_out)

    @basic_property(pressure_lose=NumericProperty(0, inf, unit='kPa'))
    def _eval_pressure_lose(self):
        id_inlet_node = self.get_id_inlet_nodes()[0]
        inlet_node = self.get_inlet_node(id_inlet_node)
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        p_in = inlet_node.pressure()
        p_out = outlet_node.pressure()
        return (p_in - p_out) / 1000.0

    def calculated_result(self, key):


        if key == self.COOLING_POWER:
            return self._eval_cooling_power()

        elif key == self.SATURATION_TEMPERATURE:
            return self._eval_saturation_temperature()

        elif key == self.SUPERHEATING:
            return self._eval_superheating()

        elif key == self.PRESSURE_LOSE:
            return self._eval_pressure_lose()
        else:
            raise PropertyNameError("Invalid property. %s  is not in %s]" % key)

    def _eval_basic_equation(self, key_basic_property):
            return [self.get_property(key_basic_property), self.calculated_result(key_basic_property)]

    def _eval_intrinsic_equations(self):
        return None
