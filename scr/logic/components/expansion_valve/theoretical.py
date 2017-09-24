# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the Expansion Valve component.
"""

from scr.logic.components.component import Component as Cmp
from scr.logic.components.component import ComponentInfo as CmpInfo
from scr.logic.components.component import component, fundamental_equation


def update_saved_data_to_last_version(orig_data, orig_version):
    return orig_data


@component('theoretical_expansion_valve', CmpInfo.EXPANSION_VALVE, 1, update_saved_data_to_last_version)
class Theoretical(Cmp):

    def __init__(self, id_, inlet_nodes_id, outlet_nodes_id, component_data):
        super().__init__(id_, inlet_nodes_id, outlet_nodes_id, component_data)

    """ Fundamental properties equations """
    @fundamental_equation()
    # function name can be arbitrary. Return a single vector with each side of the equation evaluated.
    def _eval_intrinsic_equations(self):
        id_inlet_node = self.get_id_inlet_nodes()[0]
        inlet_node = self.get_inlet_node(id_inlet_node)
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        h_in = inlet_node.enthalpy()
        h_out = outlet_node.enthalpy()

        return [h_in / 1000.0, h_out / 1000.0]
