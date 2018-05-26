# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class node.
"""

from abc import ABC, abstractmethod
from importlib import import_module
from scr.logic.errors import NodeError, BuildError, InfoFactoryError, InfoError
from scr.logic.warnings import BuildWarning
from scr.logic.refrigerants.refrigerant import Refrigerant
from scr.helpers.singleton import Singleton
from scr.helpers.properties import NumericProperty
import scr.logic.components.component as cmp
import logging as log
from typing import Dict, List, Union, Optional


class Node(ABC):
    """Node class.

    Is the class used by the solver. It's constructed with the CircuitBuilder and assume that all arguments passed are
    correct.

    All thermodynamic properties of the node are calculated from two base properties, defined in the Node child class.
    """
    def __init__(self, id_: int, components_id: List[int], refrigerant: Refrigerant) -> None:
        self._id = id_
        self._inlet_component_attached = None
        self._outlet_component_attached = None
        self._attach_components_id = components_id
        self._refrigerant = refrigerant
        self._id_mass_flow = None
        self._mass_flow = None
        # Thermodynamic properties
        self._density = None
        self._enthalpy = None
        self._entropy = None
        self._quality = None
        self._pressure = None
        self._temperature = None

    def configure(self, components_dict: Dict[int, cmp.Component], mass_flows: List[float]) -> None:
        """Configure node to solve it later."""
        for component_id in self.get_id_attach_components():
            cmp = components_dict[component_id]
            if self.get_id() in cmp.get_inlet_nodes():
                self._inlet_component_attached = components_dict[component_id]
            else:
                self._outlet_component_attached = components_dict[component_id]
        # Add to node the _mass_flows list of the circuit. Later, the specific mass flow will be configured.
        self._mass_flow = mass_flows

    def _init_essential_properties(self, property_type_1: int, property_1: float, property_type_2: int,
                                   property_2: float) -> None:
        type_property_base_1 = self.get_type_property_base_1()
        type_property_base_2 = self.get_type_property_base_2()
        if property_type_1 is type_property_base_1 and property_type_2 is type_property_base_2:
            return
        elif property_type_1 is type_property_base_2 and property_type_2 is type_property_base_1:
            return
        else:
            self._calculate_value_property_base_1(property_type_1, property_1, property_type_2, property_2)
            self._calculate_value_property_base_2(property_type_1, property_1, property_type_2, property_2)

    def _set_property(self, property_type: int, property_value: float) -> None:
        """
        :raise NodeError: property_type isn't a recognize node thermodynamic property defined in NodeInfo.
        """
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
            msg = f"The property {property_type} isn't a thermodynamic property of the node: {nd_info.TEMPERATURE}," \
                  f"{nd_info.DENSITY}, {nd_info.PRESSURE}, {nd_info.ENTHALPY}, {nd_info.ENTROPY} or {nd_info.QUALITY}."
            log.error(msg)
            raise NodeError(msg)

    @abstractmethod
    def _calculate_value_property_base_1(self, property_type_1: int, property_1: float, property_type_2: int,
                                         property_2: float) -> None:
        """Calculate and assign the value of the thermodynamic basic property 1."""
        pass

    @abstractmethod
    def _calculate_value_property_base_2(self, property_type_1: int, property_1: float, property_type_2: int,
                                         property_2: float) -> None:
        """Calculate and assign the value of the thermodynamic basic property 2."""
        pass

    def get_id(self) -> int:
        return self._id

    def get_components_attached(self) -> List[cmp.Component]:
        """Components attached to the node.

        In the first position, the first position with the component with this node as inlet node and the second one
        with this node as outlet node.
        """
        return [self.get_inlet_component_attached(), self.get_outlet_component_attached()]

    def get_inlet_component_attached(self) -> cmp.Component:
        """The component with this node as inlet node."""
        return self._inlet_component_attached

    def get_outlet_component_attached(self) -> cmp.Component:
        """The components with this node as outlet node."""
        return self._outlet_component_attached

    def get_id_attach_components(self) -> List[int]:
        return self._attach_components_id

    def get_refrigerant(self) -> Refrigerant:
        return self._refrigerant

    @abstractmethod
    def get_type_property_base_1(self) -> int:
        """Define the first physical property needed to define a thermodynamic point."""
        pass

    @abstractmethod
    def get_type_property_base_2(self) -> int:
        """Define the second physical property needed to define a thermodynamic point."""
        pass

    @abstractmethod
    def get_value_property_base_1(self) -> callable:
        """It's a pointer to the method to calculated the first physical property needed to define the node."""
        pass

    @abstractmethod
    def get_value_property_base_2(self) -> callable:
        """It's a pointer to the method to calculated the second physical property needed to define the node."""
        pass

    @abstractmethod
    def get_limits_property_base_1(self) -> List[float]:
        """[minimum value, maximum value] supported for base property 1. None if there are no limit."""
        pass

    @abstractmethod
    def get_limits_property_base_2(self) -> List[float]:
        """[minimum value, maximum value] supported for base property 2. None if there are no limit."""
        pass

    @abstractmethod
    def are_base_properties_init(self) -> bool:
        """Check if the base physical properties are calculated or not."""
        pass

    def is_mass_flow_init(self) -> bool:
        if self._id_mass_flow is not None:
            return True
        else:
            return False

    def get_id_mass_flow(self) -> int:
        return self._id_mass_flow

    def set_id_mass_flow(self, id_mass_flow) -> None:
        self._id_mass_flow = id_mass_flow

    def pressure(self) -> float:
        if self._pressure is None:
            self._pressure = self._refrigerant.p(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                 self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._pressure

    def temperature(self) -> float:
        if self._temperature is None:
            self._temperature = self._refrigerant.T(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                    self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._temperature

    def density(self) -> float:
        if self._density is None:
            self._density = self._refrigerant.d(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._density

    def enthalpy(self) -> float:
        if self._enthalpy is None:
            self._enthalpy = self._refrigerant.h(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                 self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._enthalpy

    def entropy(self) -> float:
        if self._entropy is None:
            self._entropy = self._refrigerant.s(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._entropy

    def quality(self) -> float:
        if self._quality is None:
            self._quality = self._refrigerant.Q(self.get_type_property_base_1(), self.get_value_property_base_1(),
                                                self.get_type_property_base_2(), self.get_value_property_base_2())
        return self._quality

    def mass_flow(self) -> float:
        return self._mass_flow[self._id_mass_flow]

    def update_node_values(self, property_type_1: int, property_1: float, property_type_2: int, property_2: float)\
            -> None:
        """Erase the all properties calculated and updated the node with new thermodynamic properties.

        Mass flow is not updated. It's value is stored inside the circuit that contains the node.
        """
        self._density = None
        self._enthalpy = None
        self._entropy = None
        self._quality = None
        self._pressure = None
        self._temperature = None

        self._set_property(property_type_1, property_1)
        self._set_property(property_type_2, property_2)

        self._init_essential_properties(property_type_1, property_1, property_type_2, property_2)

    def get_node_info(self) -> 'NodeInfo':
        return NodeInfoFactory.get(self)


class ANodeSerializer:
    """Serializer for the Node Class.

        Public attributes:
            - COMPONENTS
            - IDENTIFIER
    """
    IDENTIFIER = 'id'
    COMPONENTS = 'components'

    def deserialize(self, node_file: Dict) -> 'NodeBuilder':
        node = NodeBuilder(node_file[self.IDENTIFIER], node_file[self.COMPONENTS][0], node_file[self.COMPONENTS][1])
        return node

    def serialize(self, node: 'Node') -> Dict:
        return {self.IDENTIFIER: node.get_id(), self.COMPONENTS: node.get_id_attach_components()}


class NodeBuilder:
    """Builder class for Node."""
    def __init__(self, id_: int, component_id_1: Optional[int] = None, component_id_2: Optional[int] = None) -> None:
        self._id = id_
        self._components_id = []
        if component_id_1 is not None:
            self._components_id.append(component_id_1)
        if component_id_2 is not None:
            self._components_id.append(component_id_2)
        # Only used for NodeInfoFactory. Allow to NodeInfoFactory accept a NodeBuilder object.
        self._ref = None
        self._ref_lib = None

    def build(self, refrigerant_object: Refrigerant, ref_lib: str) -> Node:
        """Build the Node object.

        Check if the input data is correct.

        :raise BuildError: if fail data is incorrect.
        """

        # Return a node object.
        # Check if node have two components attached.
        if len(self._components_id) != 2:
            msg = f"Node {self.get_id()} has len(self._components_id) components attached instead of 2."
            log.error(msg)
            raise BuildError(msg)

        # Dynamic importing modules
        try:
            nd = import_module('scr.logic.nodes.' + ref_lib)
        except ImportError:
            msg = f"'Error loading node library. Type: {ref_lib} is not found."
            log.error(msg)
            raise BuildError(msg)
        aux = ref_lib.rsplit('.')
        class_name = aux.pop()
        # Only capitalize the first letter
        class_name = class_name.replace(class_name[0], class_name[0].upper(), 1)
        class_ = getattr(nd, class_name)
        return class_(self._id, self._components_id, refrigerant_object)

    def get_id(self) -> int:
        return self._id

    def add_component(self, component_id: int) -> None:
        """
        :raise BuildWarning
        """
        if component_id not in self._components_id:
            self._components_id.append(component_id)
        else:
            msg = f"Component {component_id} is already attached at the node {self.get_id()}."
            log.warning(msg)
            raise BuildWarning(msg)

    def remove_component(self, component_id: int) -> None:
        """
        :raise BuildWarning
        """
        try:
            self._components_id.remove(component_id)
        except ValueError:
            msg = f"The component {component_id} isn't attached to the node {self.get_id()}."
            raise BuildWarning(msg)

    def get_components(self) -> List[int]:
        return self._components_id

    # Only for NodeInfoFactory works with NodeBuilder object.
    def _set_refrigerant(self, refrigerant: 'scr.helpers.properties.StrRestricted') -> None:
        self._ref = refrigerant

    # Only for NodeInfoFactory works with NodeBuilder object.
    def _set_refrigerant_library(self, ref_lib: 'scr.helpers.properties.StrRestricted') -> None:
        self._ref_lib = ref_lib


#
class NodeInfo:
    """
    Information of the node.

    All information about node is store in this class. For example: limits for thermodynamic properties.
    Node supports the following properties:
        - DENSITY
        - ENTROPY
        - ENTHALPY
        - MASS_FLOW
        - PRESSURE
        - QUALITY
        - TEMPERATURE

    Only supported units in SI.
    """
    # Physic properties.
    MASS_FLOW = -1
    # Thermodynamic properties.
    DENSITY = Refrigerant.DENSITY
    ENTROPY = Refrigerant.ENTROPY
    ENTHALPY = Refrigerant.ENTHALPY
    QUALITY = Refrigerant.QUALITY
    PRESSURE = Refrigerant.PRESSURE
    TEMPERATURE = Refrigerant.TEMPERATURE

    def __init__(self, refrigerant_object: Refrigerant) -> None:
        self._ref = refrigerant_object
        self._pressure = NumericProperty(self._ref.pmin(), self._ref.pmax(), unit='Pa')
        self._temperature = NumericProperty(self._ref.Tmin(), self._ref.Tmax(), unit='K')
        self._density = NumericProperty(self._ref.dmin(), self._ref.dmax(), unit='kg/m3')
        self._enthalpy = NumericProperty(self._ref.hmin(), self._ref.hmax(), unit='J/kg')
        self._entropy = NumericProperty(self._ref.smin(), self._ref.smax(), unit='J/kg*K')
        self._quality = NumericProperty(self._ref.Qmin(), self._ref.Qmax(), unit='')
        self._mass_flow = NumericProperty(0.0, None, unit='kg/s')

    def get_properties(self) -> Dict[int, NumericProperty]:
        """Properties supported by node."""
        return {self.PRESSURE: self._pressure, self.TEMPERATURE: self._temperature, self.DENSITY: self._density,
                self.ENTHALPY: self._enthalpy, self.ENTROPY: self._entropy, self.QUALITY: self._quality,
                self.MASS_FLOW: self._mass_flow}

    def get_property(self, property_name: int) -> NumericProperty:
        """
        :raise InfoError
        """
        properties = self.get_properties()
        if property_name in properties:
            return properties[property_name]
        else:
            msg = f"PropertyName {property_name} doesn't exist in {type(self)}."
            log.error(msg)
            raise InfoError(msg)

    def get_property_limit(self, prop: int) -> List[float]:
        """
        Property limits.

        :param prop: node property.
        :return: [lower boundary, upper boundary]
        :raise InfoError: if the property doesn't exist.
        """
        return self.get_property(prop).get_limits()


# For uniform API with ComponentInfo.
class NodeInfoFactory(metaclass=Singleton):
    """Factory for NodeInfo."""
    @staticmethod
    def get(key: Union[Refrigerant, NodeBuilder, str], *args: str) -> NodeInfo:
        if isinstance(key, Node):
            ref_object = key.get_refrigerant()
        elif isinstance(key, NodeBuilder):
            ref = key._ref
            ref_lib = key._ref_lib
            if ref is None:
                msg = f"Node {NodeBuilder.get_id()} doesn't have the refrigerant selected in the NodeBuilder."
                log.error(msg)
                raise InfoFactoryError(msg)
            elif ref_lib is None:
                msg = f"Node {NodeBuilder.get_id()} doesn't have the refrigerant library selected in the NodeBuilder."
                log.error(msg)
                raise InfoFactoryError(msg)
            else:
                ref_object = Refrigerant.build(ref_lib, ref)
        elif type(key) is str:
            ref_object = Refrigerant.build(args[0], key)
        else:
            raise InfoFactoryError(f"NodeInfoFactory can't return a NodeInfo class with the argument passed: {key}")

        return NodeInfo(ref_object)
