# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the Compressor component.
"""

from scr.logic.common import MAX_FLOAT_VALUE
from scr.logic.components.component import Component as cmp
from scr.logic.errors import PropertyNameError
from scr.logic.refrigerants.refrigerant import Refrigerant

class TheoreticalInfo(InfoCMPcomp):
    DISPLACEMENT_VOLUME = 'displacement_volume'
    ISENTROPIC_EFFICIENCY = 'isentropic_efficiency'
    POWER_CONSUMPTION = 'power_consumption'
    VOLUMETRIC_EFFICIENCY = 'volumetric_efficiency'

    basic_properties_allowed = {ISENTROPIC_EFFICIENCY: {cmp.LOWER_LIMIT: 0.0, cmp.UPPER_LIMIT: 1.0, cmp.UNIT: ''},
                                POWER_CONSUMPTION: {cmp.LOWER_LIMIT: 0.0, cmp.UPPER_LIMIT: MAX_FLOAT_VALUE,
                                                    cmp.UNIT: 'kW'}}

    optional_properties_allowed = {DISPLACEMENT_VOLUME: {cmp.LOWER_LIMIT: 0.0, cmp.UPPER_LIMIT: MAX_FLOAT_VALUE,
                                                         cmp.UNIT: 'm3/h'},
                                   VOLUMETRIC_EFFICIENCY: {cmp.LOWER_LIMIT: 0.0, cmp.UPPER_LIMIT: 1.0, cmp.UNIT: ''}}
}

class TheoreticalInfo(InfoCMP):
    DISPLACEMENT_VOLUME = 'displacement_volume'
    ISENTROPIC_EFFICIENCY = 'isentropic_efficiency'
    POWER_CONSUMPTION = 'power_consumption'
    VOLUMETRIC_EFFICIENCY = 'volumetric_efficiency'

    basic_properties_allowed = {ISENTROPIC_EFFICIENCY: {cmp.LOWER_LIMIT: 0.0, cmp.UPPER_LIMIT: 1.0, cmp.UNIT: ''},
                                POWER_CONSUMPTION: {cmp.LOWER_LIMIT: 0.0, cmp.UPPER_LIMIT: MAX_FLOAT_VALUE,
                                                    cmp.UNIT: 'kW'}}

    optional_properties_allowed = {DISPLACEMENT_VOLUME: {cmp.LOWER_LIMIT: 0.0, cmp.UPPER_LIMIT: MAX_FLOAT_VALUE,
                                                         cmp.UNIT: 'm3/h'},
                                   VOLUMETRIC_EFFICIENCY: {cmp.LOWER_LIMIT: 0.0, cmp.UPPER_LIMIT: 1.0, cmp.UNIT: ''}}
}

def Theoretical(CMP):
    def __init__(self, data, circuit_nodes):
        super().__init__(data, circuit_nodes, 1, 1, self.basic_properties_allowed, self.optional_properties_allowed)
        self.disp_vol = BoundNum(.4, 0, 5)

    def reg_eval_func(self):
        self.add_func()
        func = {}
        func[self.DISPLACEMENT_VOLUME] = self.sss
        func[self.DISPLACEMENT_VOLUME] = self.sss
        func[self.DISPLACEMENT_VOLUME] = self.sss
        func[self.DISPLACEMENT_VOLUME] = self.sss

    def _calculated_result(self, key):
        id_inlet_node = list(self.get_id_inlet_nodes())[0]
        inlet_node = self.get_inlet_node(id_inlet_node)
        id_outlet_node = list(self.get_id_outlet_nodes())[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        if key == self.ISENTROPIC_EFFICIENCY:
            h_in = inlet_node.enthalpy()
            s_in = inlet_node.entropy()
            h_out = outlet_node.enthalpy()
            p_out = outlet_node.pressure()
            ref = outlet_node.get_refrigerant()
            h_is = ref.h(Refrigerant.PRESSURE, p_out, Refrigerant.ENTROPY, s_in)
            return (h_is-h_in)/(h_out-h_in)

        elif key == self.POWER_CONSUMPTION:
            h_in = inlet_node.enthalpy()
            h_out = outlet_node.enthalpy()
            mass_flow = h_out.mass_flow()
            return mass_flow * (h_out - h_in) / 1000.0

        elif key == self.VOLUMETRIC_EFFICIENCY:
            mass_flow = inlet_node.mass_flow()
            density = inlet_node.density()
            volumetric_efficiency = self.get_optional_property(key)
            return mass_flow * density / volumetric_efficiency

        elif key == self.DISPLACEMENT_VOLUME:
            mass_flow = inlet_node.mass_flow()
            density = inlet_node.density()
            displacement_volume = self.get_optional_property(key)
            return mass_flow * density / displacement_volume
        else:
            return PropertyNameError(
                    "Invalid property. %s  is not in %s]" % key)

    def _eval_basic_equation(self, basic_property):
        return [self.get_basic_property(basic_property), self._calculated_result(basic_property)]

    def _eval_intrinsic_equations(self):
        return None

    def sss(self):
        pass