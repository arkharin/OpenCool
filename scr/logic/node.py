# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class node.
"""

from abc import ABC, abstractmethod
from scr.logic.errors import PropertyNameError
from scr.logic.common import GeneralData
from scr.logic.refrigerant import Refrigerant


class Node(ABC, GeneralData):
    DENSITY = Refrigerant.DENSITY
    ENTROPY = Refrigerant.ENTROPY
    ENTHALPY = Refrigerant.ENTHALPY
    QUALITY = Refrigerant.QUALITY
    PRESSURE = Refrigerant.PRESSURE
    TEMPERATURE = Refrigerant.TEMPERATURE
    NO_INIT = None

    def __init__(self, name, identifier, refrigerant):
        super().__init__(name, identifier)
        self._attach_components = []
        self._refrigerant = refrigerant
        self._id_mass_flow = self.NO_INIT
        self._mass_flow = self.NO_INIT
        # Thermodynamic properties
        self._density = self.NO_INIT
        self._enthalpy = self.NO_INIT
        self._entropy = self.NO_INIT
        self._quality = self.NO_INIT
        self._pressure = self.NO_INIT
        self._temperature = self.NO_INIT

    def _init_essential_properties(self, property_type_1, property_1, property_type_2, property_2):
        type_property_base_1 = self.get_type_property_base_1()
        type_property_base_2 = self.get_type_property_base_2()
        if property_type_1 is type_property_base_1 and property_type_2 is type_property_base_2:
            return
        elif property_type_1 is type_property_base_2 and property_type_2 is type_property_base_1:
            return
        else:
            self._set_value_property_base_1(property_type_1, property_1, property_type_2, property_2)
            self._set_value_property_base_2(property_type_1, property_1, property_type_2, property_2)

    def _set_property(self, property_type, property_value):
        if property_type is self.TEMPERATURE:
            self._temperature = property_value

        elif property_type is self.DENSITY:
            self._density = property_value

        elif property_type is self.PRESSURE:
            self._pressure = property_value

        elif property_type is self.ENTHALPY:
            self._enthalpy = property_value

        elif property_type is self.ENTROPY:
            self._entropy = property_value

        elif property_type is self.QUALITY:
            self._quality = property_value

        else:
            raise PropertyNameError("Error in Node -> _set_property: The property is not recognize")

    @abstractmethod
    def _set_value_property_base_1(self, property_type_1, property_1, property_type_2, property_2):
        pass

    @abstractmethod
    def _set_value_property_base_2(self, property_type_1, property_1, property_type_2, property_2):
        pass

    def add_mass_flow(self, mass_flows):
        self._mass_flow = mass_flows

    def attach_component(self, component):
        id_component = component.get_id()
        id_components = []
        for component in self._attach_components:
            id_components.append(component.get_id())
        if id_component in id_components:
            return
        else:
            self._attach_components.append(component)

    def calculate_node(self):
        self._pressure = self.pressure()
        self._temperature = self.temperature()
        self._enthalpy = self.enthalpy()
        self._density = self.density()
        self._entropy = self.entropy()
        self._quality = self.quality()

    def get_components_attached(self):
        return self._attach_components

    def get_refrigerant(self):
        return self._refrigerant

    @abstractmethod
    def get_type_property_base_1(self):
        pass

    @abstractmethod
    def get_type_property_base_2(self):
        pass

    @abstractmethod
    def get_value_property_base_1(self):
        pass

    @abstractmethod
    def get_value_property_base_2(self):
        pass

    @abstractmethod
    def is_init(self):
        pass

    def is_mass_flow_init(self):
        if self._id_mass_flow is not self.NO_INIT:
            return True
        else:
            return False

    def set_id_mass_flow(self, id_mass_flow):
        self._id_mass_flow = id_mass_flow

    def pressure(self):
        if self._pressure is self.NO_INIT:
            self._pressure = self._refrigerant.p(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                 self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._pressure

    def temperature(self):
        if self._temperature is self.NO_INIT:
            self._temperature = self._refrigerant.T(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                    self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._temperature

    def density(self):
        if self._density is self.NO_INIT:
            self._density = self._refrigerant.d(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._density

    def enthalpy(self):
        if self._enthalpy is self.NO_INIT:
            self._enthalpy = self._refrigerant.h(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                 self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._enthalpy

    def entropy(self):
        if self._entropy is self.NO_INIT:
            self._entropy = self._refrigerant.s(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._entropy

    def mass_flow(self):
        return self._mass_flow[self._id_mass_flow]

    def quality(self):
        if self._quality is self.NO_INIT:
            self._quality = self._refrigerant.Q(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._quality

    def update_node_values(self, property_type_1, property_1, property_type_2, property_2):
        # Thermodynamic properties
        self._density = self.NO_INIT
        self._enthalpy = self.NO_INIT
        self._entropy = self.NO_INIT
        self._quality = self.NO_INIT
        self._pressure = self.NO_INIT
        self._temperature = self.NO_INIT

        self._set_property(property_type_1, property_1)
        self._set_property(property_type_2, property_2)

        self._init_essential_properties(property_type_1, property_1, property_type_2, property_2)
