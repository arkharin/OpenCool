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
from scr.logic.components.component import component, fundamental_property, basic_property, auxiliary_property
from scr.helpers.properties import NumericBoundary
from math import inf


def update_saved_data_to_last_version(orig_data, orig_version):
    # Here will be the code to update to update saved data to current format
    return orig_data

# Template:
#@component([key name1, key name2,...], version, function to update from old versions)
@component(['theoretical_compressor', 'isentropic_compressor'], 1, update_saved_data_to_last_version)
class Theoretical(cmp):
    DISPLACEMENT_VOLUME = 'displacement_volume'
    ISENTROPIC_EFFICIENCY = 'isentropic_efficiency'
    POWER_CONSUMPTION = 'power_consumption'
    VOLUMETRIC_EFFICIENCY = 'volumetric_efficiency'

    basic_properties_allowed = {ISENTROPIC_EFFICIENCY:
                                    {cmp.LOWER_LIMIT: 0.0,
                                     cmp.UPPER_LIMIT: 1.0,
                                     cmp.UNIT: ''},
                                POWER_CONSUMPTION:
                                    {cmp.LOWER_LIMIT: 0.0,
                                     cmp.UPPER_LIMIT: MAX_FLOAT_VALUE,
                                     cmp.UNIT: 'kW'}}

    optional_properties_allowed = {DISPLACEMENT_VOLUME: {cmp.LOWER_LIMIT: 0.0, cmp.UPPER_LIMIT: MAX_FLOAT_VALUE,
                                                         cmp.UNIT: 'm3/h'},
                                   VOLUMETRIC_EFFICIENCY: {cmp.LOWER_LIMIT: 0.0, cmp.UPPER_LIMIT: 1.0, cmp.UNIT: ''}}

    def __init__(self, name, id_, component_type, inlet_nodes_id, outlet_nodes_id, component_data):
        super().__init__(name, id_, component_type, inlet_nodes_id, outlet_nodes_id, component_data, 1, 1,
                         self.basic_properties_allowed, self.optional_properties_allowed)

    ### Fundamental properties equations ###

    ### Basic properties equations ###
    # @basic_property(name of basic property = value type)
    # Name must be only one word
    @basic_property(isentropic_efficiency=NumericBoundary(0, 1))
    # function name can be arbitrary
    def _eval_eq_isentropic_effiency(self):
        id_inlet_node = self.get_id_inlet_nodes()[0]
        inlet_node = self.get_inlet_node(id_inlet_node)
        id_outlet_node = self.get_id_outlet_nodes()[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        h_in = inlet_node.enthalpy()
        s_in = inlet_node.entropy()
        h_out = outlet_node.enthalpy()
        p_out = outlet_node.pressure()
        ref = outlet_node.get_refrigerant()
        h_is = ref.h(Refrigerant.PRESSURE, p_out, Refrigerant.ENTROPY, s_in)
        return (h_is - h_in) / (h_out - h_in)

    @basic_property(power_consumption=NumericBoundary(0, 1))
    def _eval_eq_power_consumption(self):
        id_inlet_node = list(self.get_id_inlet_nodes())[0]
        inlet_node = self.get_inlet_node(id_inlet_node)
        id_outlet_node = list(self.get_id_outlet_nodes())[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        h_in = inlet_node.enthalpy()
        h_out = outlet_node.enthalpy()
        mass_flow = outlet_node.mass_flow()
        return mass_flow * (h_out - h_in) / 1000.0

    ### Auxiliary properties equations ###
    @auxiliary_property(displacement_volume=NumericBoundary(0, inf))
    def _eval_eq_displacement_volume(self):
        id_inlet_node = list(self.get_id_inlet_nodes())[0]
        inlet_node = self.get_inlet_node(id_inlet_node)
        id_outlet_node = list(self.get_id_outlet_nodes())[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        mass_flow = inlet_node.mass_flow()
        density = inlet_node.density()
        # Remember, magics has happpened and all static
        # attributes have been transformed to instance attributes
        # and primitive types ;)
        return mass_flow * density / self.displacement_volume

    @auxiliary_property(volumetric_efficiency=NumericBoundary(0, 1))
    def _eval_eq_volumetric_efficiency(self):
        id_inlet_node = list(self.get_id_inlet_nodes())[0]
        inlet_node = self.get_inlet_node(id_inlet_node)
        id_outlet_node = list(self.get_id_outlet_nodes())[0]
        outlet_node = self.get_outlet_node(id_outlet_node)

        mass_flow = inlet_node.mass_flow()
        density = inlet_node.density()
        # Remember, magics has happpened and all static
        # attributes have been transformed to instance attributes
        # and primitive types ;)
        return mass_flow * density / self.volumetric_efficiency

    def calculated_result(self, key):
        if key == self.ISENTROPIC_EFFICIENCY:
            return self._eval_eq_isentropic_effiency()

        elif key == self.POWER_CONSUMPTION:
            return self._eval_eq_power_consumption()

        elif key == self.VOLUMETRIC_EFFICIENCY:
            return self._eval_eq_volumetric_efficiency()

        elif key == self.DISPLACEMENT_VOLUME:
            return self._eval_eq_displacement_volume()

        else:
            return PropertyNameError(
                "Invalid property. %s  is not in %s]" % key)

    def _eval_basic_equation(self, key_basic_property):
        return [self.get_basic_property(key_basic_property), self.calculated_result(key_basic_property)]

    def _eval_intrinsic_equations(self):
        return None
