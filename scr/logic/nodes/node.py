# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class node.
"""

from abc import ABC, abstractmethod
from importlib import import_module
from scr.logic.restricted_inputs import StrRestricted
from scr.logic.base_classes import Element
from scr.logic.errors import PropertyNameError, NodeBuilderError, BuildError
from scr.logic.warnings import NodeBuilderWarning
from scr.logic.refrigerants.refrigerant import Refrigerant


class Node(ABC, Element):
    NAME = 'name'
    IDENTIFIER = 'id'
    # Thermodynamic properties
    DENSITY = Refrigerant.DENSITY
    ENTROPY = Refrigerant.ENTROPY
    ENTHALPY = Refrigerant.ENTHALPY
    QUALITY = Refrigerant.QUALITY
    PRESSURE = Refrigerant.PRESSURE
    TEMPERATURE = Refrigerant.TEMPERATURE
    NO_INIT = None

    def __init__(self, name, id_, components_id, refrigerant_object):
        super().__init__(name, id_)
        self._inlet_component_attached = None
        self._outlet_component_attached = None
        self._attach_components_id = components_id
        self._refrigerant = refrigerant_object
        self._id_mass_flow = self.NO_INIT
        self._mass_flow = self.NO_INIT
        # Thermodynamic properties
        self._density = self.NO_INIT
        self._enthalpy = self.NO_INIT
        self._entropy = self.NO_INIT
        self._quality = self.NO_INIT
        self._pressure = self.NO_INIT
        self._temperature = self.NO_INIT

    def configure(self, components_dict):
        for component_id in self.get_id_attach_components():
            cmp = components_dict[component_id]
            if self.get_id() in cmp.get_inlet_nodes():
                self._inlet_component_attached = components_dict[component_id]
            else:
                self._outlet_component_attached = components_dict[component_id]

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

    def get_components_attached(self):
        # Return a list of attached components.
        return [self.get_inlet_component_attached(), self.get_outlet_component_attached()]

    def get_inlet_component_attached(self):
        # Return a list with all components with this node as inlet node
        return self._inlet_component_attached

    def get_outlet_component_attached(self):
        # Return a list with all components with this node as outlet node
        return self._outlet_component_attached

    def get_id_attach_components(self):
        return self._attach_components_id

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


class ANodeSerializer:
    NAME = 'name'
    IDENTIFIER = 'id'
    COMPONENTS = 'components'
    UNIT = 'Units'

    def __init__(self):
        pass

    def deserialize(self, node_file):
        node = NodeBuilder(node_file[self.IDENTIFIER], node_file[self.COMPONENTS][0], node_file[self.COMPONENTS][1])
        node.set_name(node_file[self.NAME])
        return node

    def serialize(self, node):
        return {self.NAME: node.get_name(), self.IDENTIFIER: node.get_id(), self.UNIT: 'All units in SI',
                'Results': self._get_properties(node), self.COMPONENTS: node.get_id_attach_components()}

    def _get_properties(self, node):
        # Return dict with thermodynamic properties evaluated. Keys are global name of the properties.
        properties = {'pressure': node.pressure()}
        properties['temperature'] = node.temperature()
        properties['enthalpy'] = node.enthalpy()
        properties['density'] = node.density()
        properties['entropy'] = node.entropy()
        properties['quality'] = node.quality()
        return properties


class NodeBuilder:
    def __init__(self, id_, component_id_1, component_id_2):
        self._name = None
        self._id = id_
        self._components_id = [component_id_1, component_id_2]

    def build(self, refrigerant_object, ref_lib):
        # Return a node object.
        if self._name is None:
            raise NodeBuilderWarning('Node %s has no name', self.get_id())
        # Check if node have two components attached.
        if len(self._components_id) != 2:
            raise BuildError('Node %s has %s components attached', (self._name, len(self._components_id)))

        # Dynamic importing modules
        try:
            nd = import_module('scr.logic.nodes.' + ref_lib)
        except ImportError:
            print('Error loading node library. Type: %s is not found', ref_lib)
            exit(1)
        aux = ref_lib.rsplit('.')
        class_name = aux.pop()
        # Only capitalize the first letter
        class_name = class_name.replace(class_name[0], class_name[0].upper(), 1)
        class_ = getattr(nd, class_name)
        return class_(self._name, self._id, self._components_id, refrigerant_object)

    def set_name(self, name):
        self._name = StrRestricted(name)

    def get_id(self):
        return self._id

    def add_component(self, component_id):
        if component_id not in self._components_id:
            self._components_id.append(component_id)
        else:
            raise NodeBuilderWarning('This component is already attached at this node')

    def remove_component(self, component_id):
        try:
            self._components_id.remove(component_id)
        except ValueError:
            raise NodeBuilderWarning('This component is not attached to the node')

    def get_components_id(self):
        return self._components_id
