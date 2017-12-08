# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the Condenser component.
If pressure is higher than critical point, saturation properties are evaluated at critical point.
"""

from scr.logic.components.component import Component as Cmp
from scr.logic.components.component import ComponentInfo as CmpInfo
from scr.logic.components.component import component, basic_property
from scr.helpers.properties import NumericProperty
from math import inf


def update_saved_data_to_last_version(orig_data, orig_version):
    return orig_data


@component('theoretical_condenser', CmpInfo.CONDENSER, 1, update_saved_data_to_last_version)
class Theoretical(Cmp):
    HEATING_POWER = 'heating_power'
    PRESSURE_LOSE = 'pressure_lose'
    SATURATION_TEMPERATURE = 'saturation_temperature'
    SUBCOOLING = 'subcooling'

    def __init__(self, id_, inlet_nodes_id, outlet_nodes_id, component_data):
        super().__init__(id_, inlet_nodes_id, outlet_nodes_id, component_data)

    @basic_property(heating_power=NumericProperty(0, inf, unit='kW'))
    def _eval_heating_power(self):
        id_inlet_node = self.get_id_inlet_nodes()[0]
        inlet_node = self.get_inlet_node(id_inlet_node)
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)
        h_in = inlet_node.enthalpy()
        h_out = outlet_node.enthalpy()
        mass_flow = outlet_node.mass_flow()
        return mass_flow * (h_in - h_out) / 1000.0

    @basic_property(saturation_temperature=NumericProperty(0, inf, unit='K'))
    def _eval_saturation_temperature(self):
        id_inlet_node = self.get_id_inlet_nodes()[0]
        inlet_node = self.get_inlet_node(id_inlet_node)

        p_in = inlet_node.pressure()
        ref = inlet_node.get_refrigerant()
        # If the pressure is higher than critical pressure, there are no saturation temperature. In  this case, critical
        # temperature will be used.
        p_critical = ref.p_crit()
        if p_in >= p_critical:
            # TODO raise a warning
            return ref.T_crit()
        else:
            return ref.T_sat(p_in)

    @basic_property(subcooling=NumericProperty(0, inf, unit='K'))
    def _eval_subcooling(self):
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        t_out = outlet_node.temperature()
        p_out = outlet_node.pressure()
        ref = outlet_node.get_refrigerant()
        # If the pressure is higher than critical pressure, there are no saturation temperature. In  this case, critical
        # temperature will be used.
        p_critical = ref.p_crit()
        if p_out >= p_critical:
            # TODO raise a warning
            t_sat = ref.T_crit()
        else:
            t_sat = ref.T_sat(p_out)

        return t_sat - t_out

    @basic_property(pressure_lose=NumericProperty(0, inf, unit='kPa'))
    def _eval_pressure_loss(self):
        id_inlet_node = self.get_id_inlet_nodes()[0]
        inlet_node = self.get_inlet_node(id_inlet_node)
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        p_in = inlet_node.pressure()
        p_out = outlet_node.pressure()
        return (p_in - p_out) / 1000.0
