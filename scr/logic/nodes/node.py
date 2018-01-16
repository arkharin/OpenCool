# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class node.
"""

from abc import ABC, abstractmethod
from importlib import import_module
from scr.logic.errors import PropertyNameError, BuildError, InfoFactoryError
from scr.logic.warnings import NodeBuilderWarning
from scr.logic.refrigerants.refrigerant import Refrigerant
from scr.helpers.singleton import Singleton
from scr.helpers.properties import NumericProperty


class Node(ABC):
    def __init__(self, id_, components_id, refrigerant_object):
        self._id = id_
        self._inlet_component_attached = None
        self._outlet_component_attached = None
        self._attach_components_id = components_id
        self._refrigerant = refrigerant_object
        self._id_mass_flow = None
        self._mass_flow = None
        # Thermodynamic properties
        self._density = None
        self._enthalpy = None
        self._entropy = None
        self._quality = None
        self._pressure = None
        self._temperature = None

    def configure(self, components_dict, mass_flows):
        for component_id in self.get_id_attach_components():
            cmp = components_dict[component_id]
            if self.get_id() in cmp.get_inlet_nodes():
                self._inlet_component_attached = components_dict[component_id]
            else:
                self._outlet_component_attached = components_dict[component_id]
        # Add to node the _mass_flows list of the circuit. Later, the specific mass flow will be configured.
        self._mass_flow = mass_flows

    def _init_essential_properties(self, property_type_1, property_1, property_type_2, property_2):
        type_property_base_1 = self.get_type_property_base_1()
        type_property_base_2 = self.get_type_property_base_2()
        if property_type_1 is type_property_base_1 and property_type_2 is type_property_base_2:
            return
        elif property_type_1 is type_property_base_2 and property_type_2 is type_property_base_1:
            return
        else:
            self._calculate_value_property_base_1(property_type_1, property_1, property_type_2, property_2)
            self._calculate_value_property_base_2(property_type_1, property_1, property_type_2, property_2)

    def _set_property(self, property_type, property_value):
        nd_info = self.get_node_info()
        if property_type is nd_info.TEMPERATURE:
            self._temperature = property_value

        elif property_type is nd_info.DENSITY:
            self._density = property_value

        elif property_type is nd_info.PRESSURE:
            self._pressure = property_value

        elif property_type is nd_info.ENTHALPY:
            self._enthalpy = property_value

        elif property_type is nd_info.ENTROPY:
            self._entropy = property_value

        elif property_type is nd_info.QUALITY:
            self._quality = property_value

        else:
            raise PropertyNameError("Error in Node -> _set_property: The property is not recognize")

    @abstractmethod
    def _calculate_value_property_base_1(self, property_type_1, property_1, property_type_2, property_2):
        pass

    @abstractmethod
    def _calculate_value_property_base_2(self, property_type_1, property_1, property_type_2, property_2):
        pass

    def get_id(self):
        return self._id

    def get_components_attached(self):
        # Return a list of attached components.
        return [self.get_inlet_component_attached(), self.get_outlet_component_attached()]

    def get_inlet_component_attached(self):
        # Return the component with this node as inlet node
        return self._inlet_component_attached

    def get_outlet_component_attached(self):
        # Return the components with this node as outlet node
        return self._outlet_component_attached

    def get_id_attach_components(self):
        return self._attach_components_id

    def get_refrigerant(self):
        return self._refrigerant

    @abstractmethod
    def get_type_property_base_1(self):
        # Define the first physical property needed to define a thermodynamic point.
        pass

    @abstractmethod
    def get_type_property_base_2(self):
        # Define the second physical property needed to define a thermodynamic point.
        pass

    @abstractmethod
    def get_value_property_base_1(self):
        # It's a pointer to the method to calculated the first physical property needed to define the node.
        pass

    @abstractmethod
    def get_value_property_base_2(self):
        # It's a pointer to the method to calculated the second physical property needed to define the node.
        pass

    @abstractmethod
    def get_limits_property_base_1(self):
        # Return a tuple with (minimum value, maximum value) supported for base property 1. None if there are no limit.
        pass

    @abstractmethod
    def get_limits_property_base_2(self):
        # Return a tuple with (minimum value, maximum value) supported for base property 2. None if there are no limit.
        pass

    @abstractmethod
    def are_base_properties_init(self):
        # Check if the base physical properties are calculated or not.
        pass

    def is_mass_flow_init(self):
        if self._id_mass_flow is not None:
            return True
        else:
            return False

    def get_id_mass_flow(self):
        return self._id_mass_flow

    def set_id_mass_flow(self, id_mass_flow):
        self._id_mass_flow = id_mass_flow

    def pressure(self):
        if self._pressure is None:
            self._pressure = self._refrigerant.p(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                 self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._pressure

    def temperature(self):
        if self._temperature is None:
            self._temperature = self._refrigerant.T(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                    self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._temperature

    def density(self):
        if self._density is None:
            self._density = self._refrigerant.d(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._density

    def enthalpy(self):
        if self._enthalpy is None:
            self._enthalpy = self._refrigerant.h(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                 self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._enthalpy

    def entropy(self):
        if self._entropy is None:
            self._entropy = self._refrigerant.s(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._entropy

    def quality(self):
        if self._quality is None:
            self._quality = self._refrigerant.Q(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._quality

    def mass_flow(self):
        return self._mass_flow[self._id_mass_flow]

    def update_node_values(self, property_type_1, property_1, property_type_2, property_2):
        # Erase the all properties calculated and updated the node with new thermodynamic properties.
        self._density = None
        self._enthalpy = None
        self._entropy = None
        self._quality = None
        self._pressure = None
        self._temperature = None

        self._set_property(property_type_1, property_1)
        self._set_property(property_type_2, property_2)

        self._init_essential_properties(property_type_1, property_1, property_type_2, property_2)

    def get_node_info(self):
        return NodeInfoFactory.get(self)

class ANodeSerializer:
    IDENTIFIER = 'id'
    COMPONENTS = 'components'

    def deserialize(self, node_file):
        node = NodeBuilder(node_file[self.IDENTIFIER], node_file[self.COMPONENTS][0], node_file[self.COMPONENTS][1])
        return node

    def serialize(self, node):
        return {self.IDENTIFIER: node.get_id(), self.COMPONENTS: node.get_id_attach_components()}


class NodeBuilder:
    def __init__(self, id_, component_id_1, component_id_2):
        self._id = id_
        self._components_id = [component_id_1, component_id_2]
        # Only used for NodeInfoFactory. Allow to NodeInfoFactory accept a NodeBuilder object.
        self._ref = None
        self._ref_lib = None

    def build(self, refrigerant_object, ref_lib):
        # Return a node object.
        # Check if node have two components attached.
        if len(self._components_id) != 2:
            raise BuildError('Node %s has %s components attached', (self.get_id(), len(self._components_id)))

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
        return class_(self._id, self._components_id, refrigerant_object)

    def get_id(self):
        return self._id

    def add_component(self, component_id):
        if component_id not in self._components_id:
            self._components_id.append(component_id)
        else:
            raise NodeBuilderWarning('Component' + component_id + ' is already attached at the node ' + self.get_id())

    def remove_component(self, component_id):
        try:
            self._components_id.remove(component_id)
        except ValueError:
            raise NodeBuilderWarning('This component is not attached to the node')

    def get_components(self):
        return self._components_id

    # Only for NodeInfoFactory works with NodeBuilder object.
    def _set_refrigerant(self, refrigerant):
        self._ref = refrigerant

    # Only for NodeInfoFactory works with NodeBuilder object.
    def _set_refrigerant_library(self, ref_lib):
        self._ref_lib = ref_lib


#
class NodeInfo:
    # Only supported units in SI.
    MASS_FLOW = -1
    # Thermodynamic properties.
    DENSITY = Refrigerant.DENSITY
    ENTROPY = Refrigerant.ENTROPY
    ENTHALPY = Refrigerant.ENTHALPY
    QUALITY = Refrigerant.QUALITY
    PRESSURE = Refrigerant.PRESSURE
    TEMPERATURE = Refrigerant.TEMPERATURE

    def __init__(self, refrigerant_object):
        self._ref = refrigerant_object
        self._pressure = NumericProperty(self._ref.pmin(), self._ref.pmax(), unit='Pa')
        self._temperature = NumericProperty(self._ref.Tmin(), self._ref.Tmax(), unit='K')
        self._density = NumericProperty(self._ref.dmin(), self._ref.dmax(), unit='kg/m3')
        self._enthalpy = NumericProperty(self._ref.hmin(), self._ref.hmax(), unit='J/kg')
        self._entropy = NumericProperty(self._ref.smin(), self._ref.smax(), unit='J/kg*K')
        self._quality = NumericProperty(self._ref.Qmin(), self._ref.Qmax(), unit='')
        self._mass_flow = NumericProperty(0.0, None, unit='kg/s')

    def get_properties(self):
        # Return a dict of properties supported by node.
        return {self.PRESSURE: self._pressure, self.TEMPERATURE: self._temperature, self.DENSITY: self._density,
                self.ENTHALPY: self._enthalpy, self.ENTROPY: self._entropy, self.QUALITY: self._quality,
                self.MASS_FLOW: self._mass_flow}

    def get_property(self, property_name):
        properties = self.get_properties()
        if property_name in properties:
            return properties[property_name]
        else:
            raise PropertyNameError('Property ' + str(property_name) + ' is not possible in ' + str(type(self)))

    def get_property_limit(self, prop):
        return self.get_property(prop).get_limits()


# For uniform API with ComponentInfo.
class NodeInfoFactory(metaclass=Singleton):
    def __init__(self):
        pass

    @staticmethod
    def get(key, *args):
        if isinstance(key, Node):
            return NodeInfo(key.get_refrigerant())
        elif isinstance(key, NodeBuilder):
            ref = key._ref
            ref_lib = key._ref_lib
            return Refrigerant.build(ref_lib, ref)
        elif type(key) is str:
            return Refrigerant.build(key, args[0])
        else:
            raise InfoFactoryError('NodeInfoFactory can\'t return a NodeInfo class with the argument passed: ' + key)

