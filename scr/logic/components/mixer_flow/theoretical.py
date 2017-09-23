# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the Mixer Flow component.
"""
from scr.logic.components.component import Component as Cmp
from scr.logic.errors import PropertyNameError
from scr.logic.components.component import component, fundamental_equation, basic_property
from scr.helpers.properties import NumericProperty
from math import inf


def update_saved_data_to_last_version(orig_data, orig_version):
    return orig_data


@component('theoretical_mixer_flow', Cmp.MIXER_FLOW, 1, update_saved_data_to_last_version, inlet_nodes=1,
           outlet_nodes=1)
class Theoretical(Cmp):
    PRESSURE_LOSE_1 = 'pressure lose inlet 1 - outlet'
    PRESSURE_LOSE_2 = 'pressure lose inlet 2 - outlet'

    def __init__(self, data, circuit_nodes):
        super().__init__(data, circuit_nodes)

    @basic_property(pressure_lose_1=NumericProperty(0, inf, unit='kPa'))
    def _eval_pressure_lose_1(self):
        id_inlet_nodes = self.get_id_inlet_nodes()
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        inlet_node_1 = self.get_inlet_node(id_inlet_nodes[0])
        p_in = inlet_node_1.pressure()
        p_out = outlet_node.pressure()
        return (p_in - p_out) / 1000.0

    @basic_property(pressure_lose_2=NumericProperty(0, inf, unit='kPa'))
    def _eval_pressure_lose_2(self):
        id_inlet_nodes = self.get_id_inlet_nodes()
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        inlet_node_2 = self.get_inlet_node(id_inlet_nodes[1])
        p_in = inlet_node_2.pressure()
        p_out = outlet_node.pressure()
        return (p_in - p_out) / 1000.0

    @fundamental_equation()
    def _eval_intrinsic_equations_enthalpy(self):
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

        return [mass_flow_in_1 * h_in_1 + mass_flow_in_2 * h_in_2, mass_flow_out * h_out]
