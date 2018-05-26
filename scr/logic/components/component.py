# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class component.
"""
import inspect
from abc import ABC
from scr.helpers.properties import StrRestricted, NumericProperty
from scr.logic.errors import ComponentDecoratorError, ComponentError, BuildError, DeserializerError, InfoFactoryError, \
    InfoError, PropertyValueError
from scr.logic.warnings import BuildWarning
from scr.helpers.singleton import Singleton
import logging as log
from typing import Callable, List, Dict, Tuple, Optional, Union

''' Decorators to use in component plugins to register them in ComponentFactory and ComponentInfoFactory.'''


# See question 5929107 (python decorators with parameters) in stackoverflow
# See question 2366713 (Can a Python decorator of an instance method access the class?) in StackOverflow to know about
# how to solve the problem that method decorators are called when class doesn't exist yet. I implemented the same
# solution used by flask-classy. Be aware that methods in classes are bounded functions and therefore points to closure
# variables and are share between instances


def component(key: str, component_type: str, version: int = 1, updater_data_func: Callable = None, inlet_nodes: int = 1,
              outlet_nodes: int = 1) -> 'Component':
    """Decorator. Register the component child in ComponentInfo.

    :param key: name of the component. The name is unique
    :param component_type: one of component type defined in ComponentInfo.
    :param version: version of the component. First version = 1
    :param updater_data_func: function that updated the data loaded from previous version to the current version. Only
                              required if version > 1.
    :param inlet_nodes: number of inlet nodes.
    :param outlet_nodes: number of outlet nodes.
    :return: class
    :raise ComponentDecoratorError
    """

    def real_decorator(cls: Component) -> Component:
        """The decorator."""
        # updater_data_func is only required if version is bigger than 1.
        if not issubclass(cls, Component):
            msg = f"@component decorator can be use only to decorate components subclasses. Not allowable in {key}."
            log.error(msg)
            raise ComponentDecoratorError(msg)

        if version != 1 and updater_data_func is None:
            msg = f"updater_data_func must be exist if version of {key} is not 1."
            log.error(msg)
            raise ComponentDecoratorError(msg)

        cmp_info = ComponentInfo(key, cls, component_type, component_version=version,
                                 updater_data_func=updater_data_func, inlet_nodes=inlet_nodes,
                                 outlet_nodes=outlet_nodes)

        # Search those functions in the class that has been decorated with *_property decorator and add info in
        # to component info
        for member in vars(cls).values():
            if callable(member) and hasattr(member, '_property_type'):
                if member._property_type == 'fundamental':
                    pass  # It's an equation, not a property. It doesn't have name.
                elif member._property_type == 'basic':
                    cmp_info.add_basic_property(member._property_name, member._property_value)
                elif member._property_type == 'auxiliary':
                    cmp_info.add_auxiliary_property(member._property_name, member._property_value)
                else:
                    msg = f"The property {member._property_name} of the component {key} have the type unknown " \
                          f"({member._property_type})."
                    log.error(msg)
                    raise ComponentDecoratorError(msg)

        ComponentInfoFactory().add(cmp_info)
        ComponentFactory().add(key, cls)

        return cls

    return real_decorator


def fundamental_equation() -> Callable:
    """Decorator to establish that it is a fundamental equation of the component."""

    def real_decorator(func):
        setattr(func, '_property_type', 'fundamental')
        return func

    return real_decorator


def basic_property(**kwargs: Tuple) -> Callable:
    """Decorator to establish that it is a basic equation of the component.

    :raise ComponentDecoratorError
    """

    def real_decorator(func):
        if len(kwargs) != 1:
            msg = "basic_property decorator must be called with one keyword argument that it will be the property name."
            log.error(msg)
            raise ComponentDecoratorError(msg)
        # Because we are lazy. It's the fastest way to have the key and value. Only iterate one time
        for property_name, value in kwargs.items():
            setattr(func, '_property_name', property_name)
            setattr(func, '_property_type', 'basic')
            setattr(func, '_property_value', value)

        return func

    return real_decorator


def auxiliary_property(**kwargs: Tuple) -> Callable:
    """Decorator to establish that it is a auxiliary equation of the component.

    :raise ComponentDecoratorError
    """

    def real_decorator(func):
        if len(kwargs) != 1:
            msg = "auxiliary_property decorator must be called with one keyword argument that it will be the property" \
                  " name."
            log.error(msg)
            raise ComponentDecoratorError(msg)
        # Because we are lazy. It's the fastest way to have the key and value. Only iterate one time
        for property_name, value in kwargs.items():
            setattr(func, '_property_name', property_name)
            setattr(func, '_property_type', 'auxiliary')
            setattr(func, '_property_value', value)

        return func

    return real_decorator


''' End of the decorators to use in component plugins to register them in ComponentFactory and ComponentInfoFactory.'''


class Component(ABC):
    """Component class.

    Class used in the solver and represents an abstract component. All components in the circuit are child of this
    class.
    Component have:
    - Fundamental properties: properties intrinsically of the component. The equation to solve not require any external
                            value. For example in a theoretical expansion valve the relation between inlet and outlet
                            enthalpies.
    - Basic properties: properties that must be solved at the same time of the circuit. For example, the isentropic
                        efficiency of a compressor.
    - Auxiliary properties: properties that are solve once the circuit is solved.
    """

    def __init__(self, id_: int, inlet_nodes_id: List[int], outlet_nodes_id: List[int],
                 component_data: Dict[str, float]) -> None:
        """
        :raise ComponentError
        """

        self._id = id_
        self._inlet_nodes = inlet_nodes_id
        self._outlet_nodes = outlet_nodes_id
        self._basic_properties = {}
        self._auxiliary_properties = {}

        # Create and register the properties and equations. The only use is for register equations functions.
        self._fundamental_eqs = []
        self._basic_eqs = {}
        self._auxiliary_eqs = {}

        # Search those functions in the class that has been decorated with *_property decorator
        # and add equations dictionaries
        for s_attribute in dir(self):
            attribute = getattr(self, s_attribute)
            if callable(attribute) and hasattr(attribute, '_property_type'):
                if hasattr(attribute, '_property_name'):
                    property_name = attribute._property_name
                    if not hasattr(self, property_name):
                        setattr(self, property_name, None)
                    else:
                        msg = f"PropertyName {property_name} has already been defined in component {self._id}."
                        log.error(msg)
                        raise ComponentError(msg)

                    if attribute._property_type == 'basic':
                        self._basic_eqs[property_name] = attribute
                    elif attribute._property_type == 'auxiliary':
                        self._auxiliary_eqs[property_name] = attribute
                    else:
                        msg = f"The property {attribute._property_name} of the component {self._id} have the type " \
                              f"unknown ({attribute._property_type})."
                        log.error(msg)
                        raise ComponentError(msg)

                elif attribute._property_type == 'fundamental':
                    self._fundamental_eqs.append(attribute)
                else:
                    msg = f"The property {attribute._property_name} of the component {self._id} have the type " \
                          f"unknown ({attribute._property_type})."
                    log.error(msg)
                    raise ComponentError(msg)

        for property_name, property_value in component_data.items():
            if hasattr(self, property_name):
                setattr(self, property_name, property_value)
                if property_name in self._basic_eqs:
                    self._basic_properties[property_name] = property_value
                elif property_name in self._auxiliary_eqs:
                    self._auxiliary_properties[property_name] = property_value
                else:
                    msg = f"The property {property_name} of the component {self._id} have the type unknown " \
                          f"({property_type})."
                    log.error(msg)
                    raise ComponentError(msg)
            else:
                msg = f"The property {property_name} of the component {self._id} is unknown."
                log.error(msg)
                raise ComponentError(msg)

    def configure(self, nodes_dict: Dict[int, 'scr.logic.nodes.node.Node']) -> None:
        """Configure component to solve it later."""
        nodes_id = self._inlet_nodes
        self._inlet_nodes = {}
        for node_id in nodes_id:
            self._inlet_nodes[node_id] = nodes_dict[node_id]
        nodes_id = self._outlet_nodes
        self._outlet_nodes = {}
        for node_id in nodes_id:
            self._outlet_nodes[node_id] = nodes_dict[node_id]

    def eval_equations(self) -> List[List[float]]:
        """Evaluated fundamental and basic properties equations."""
        # Return a matrix of two columns with the calculation result of each side of the equation.
        results = []

        # Intrinsic equations evaluation
        for func in self._fundamental_eqs:
            # Intrinsic equations return a single vector
            results.append(func())
        # basic equations evaluation
        for key in self.get_basic_properties():
            # Basic properties return the equation evaluated.
            results.append([self.get_property(key), self._basic_eqs[key]()])

        return results

    def solve_property(self, key: str) -> Optional[float]:
        """Solve the property of the component. If it doesn't exist, return None."""
        if key in self.get_basic_properties():
            return self._basic_eqs[key]()

        elif key in self.get_auxiliary_properties():
            return self._auxiliary_eqs[key]()

    # General methods:
    def get_id(self) -> int:
        return self._id

    def get_basic_properties(self) -> Dict[str, float]:
        return self._basic_properties

    def get_auxiliary_properties(self) -> Dict[str, float]:
        # Return an array of dictionaries. Each dictionary in the format of example output components to interface.
        return self._auxiliary_properties

    def get_property(self, key):
        return getattr(self, key)

    def get_inlet_nodes(self) -> Union[List[int], Dict[int, 'scr.logic.nodes.node.Node']]:
        """
        If the component is not configured return a list, otherwise a dict.
        All inlet nodes of the component, keys ordered by lowest to higher pressure. For example, first node of two
        stage compressor is the suction). Equally pressure without specific order.
        """
        return self._inlet_nodes

    def get_id_inlet_nodes(self) -> List[int]:
        return list(self.get_inlet_nodes().keys())

    def get_inlet_node(self, id_node: int) -> 'scr.logic.nodes.node.Node':
        return self.get_inlet_nodes()[id_node]

    def get_nodes(self) -> Dict[int, 'scr.logic.nodes.node.Node']:
        """All nodes connected with the component. First inlet nodes."""
        return {**self.get_inlet_nodes(), **self.get_outlet_nodes()}

    def get_node(self, id_node: int) -> 'scr.logic.nodes.node.Node':
        return self.get_nodes()[id_node]

    def get_outlet_nodes(self) -> Union[List[int], Dict[int, 'scr.logic.nodes.node.Node']]:
        """Same of get_inlet_nodes()"""
        return self._outlet_nodes

    def get_outlet_node(self, id_node: int) -> 'scr.logic.nodes.node.Node':
        return self.get_outlet_nodes()[id_node]

    def get_id_outlet_nodes(self) -> List[int]:
        # Return a list of all outlet nodes of the component
        return list(self.get_outlet_nodes().keys())

    def get_component_info(self) -> 'ComponentInfo':
        return ComponentInfoFactory().get(self)


class AComponentSerializer(ABC):
    """Serializer for the Component Class.

    Public attributes:
        - BASIC_PROPERTIES
        - COMPONENTS
        - COMPONENT_TYPE
        - IDENTIFIER
        - INLET_NODES
        - NODES
        - AUXILIARY_PROPERTIES
        - OUTLET_NODES
        - VERSION
    """
    # TODO Serializer and deserializer doesn't take into account the units.
    # Parameters
    BASIC_PROPERTIES = 'basic properties'
    COMPONENTS = 'components'
    COMPONENT_TYPE = 'type'
    IDENTIFIER = 'id'
    INLET_NODES = 'inlet nodes'
    NODES = 'nodes'
    AUXILIARY_PROPERTIES = 'auxiliary properties'
    OUTLET_NODES = 'outlet nodes'
    VERSION = 'version'

    def deserialize(self, component_file: Dict) -> 'ComponentBuilder':
        """
        :raise DeserializerError
        """
        cmp_data = component_file
        cmp = ComponentBuilder(cmp_data[self.IDENTIFIER], cmp_data[self.COMPONENT_TYPE])
        cmp_version = cmp_data[self.VERSION]
        cmp_info = ComponentInfoFactory().get(cmp.get_component_type())
        component_version = cmp_info.get_version()
        if cmp_version < component_version:
            cmp_data = cmp_info.get_updater_data_func(cmp_data, cmp_version)
        elif cmp_version > component_version:
            msg = f"The version of component {self.IDENTIFIER} is greater than component in library. Version " \
                  f"{str(cmp_version)} vs {str(component_version)}."
            log.error(msg)
            raise DeserializerError(msg)
        i = 0
        for node_id in cmp_data[self.INLET_NODES]:
            cmp.add_inlet_node(i, node_id)
            i += 1
        i = 0
        for node_id in cmp_data[self.OUTLET_NODES]:
            cmp.add_outlet_node(i, node_id)
            i += 1
        # TODO The units are not chequed. In the builder neither.
        for key in cmp_data[self.BASIC_PROPERTIES]:
            cmp.set_attribute(key, cmp_data[self.BASIC_PROPERTIES][key])
        for key in cmp_data[self.AUXILIARY_PROPERTIES]:
            cmp.set_attribute(key, cmp_data[self.AUXILIARY_PROPERTIES][key])

        return cmp

    def serialize(self, component: Component) -> Dict:
        cmp_serialized = {self.IDENTIFIER: component.get_id()}
        cmp_serialized[self.VERSION] = component.get_component_info().get_version()
        cmp_serialized[self.COMPONENT_TYPE] = component.get_component_info().get_component_key()
        cmp_serialized[self.INLET_NODES] = component.get_id_inlet_nodes()
        cmp_serialized[self.OUTLET_NODES] = component.get_id_outlet_nodes()
        self._serialize_properties(cmp_serialized, self.BASIC_PROPERTIES, component.get_basic_properties())
        self._serialize_properties(cmp_serialized, self.AUXILIARY_PROPERTIES,
                                   component.get_auxiliary_properties())
        return cmp_serialized

    def _serialize_properties(self, cmp_serialized, properties_type, properties):
        cmp_serialized[properties_type] = {}
        for i in properties:
            cmp_serialized[properties_type][i] = properties[i]


class ComponentBuilder:
    """Builder class for component."""
    def __init__(self, id_: int, component_type: str) -> None:
        """
        :raise BuildWaring: if component_type is not a string.
        """
        self._id = id_
        try:
            self._component_type = StrRestricted(component_type)
        except PropertyValueError as e:
            log.warning(e)
            raise BuildWarning(e)
        self._component_data = {}
        self._component_info = ComponentInfoFactory().get(self.get_component_type())
        self._inlet_nodes_id = [None] * self._component_info.get_inlet_nodes()
        self._outlet_nodes_id = [None] * self._component_info.get_outlet_nodes()

    def build(self) -> Component:
        """Build the Component object.

        Check if the input data is correct.

        :raise BuildError: if fail data is incorrect.
        """
        # Check that all nodes are connected
        if None in self._inlet_nodes_id:
            msg = f"Missing nodes attached to the inlet of the component {self.get_id()}."
            log.error(msg)
            raise BuildError(msg)

        if None in self._outlet_nodes_id:
            msg = f"Missing nodes attached to the outlet of the component {self.get_id()}."
            log.error(msg)
            raise BuildError(msg)
        try:
            return ComponentFactory().create(self.get_component_type(), self._id, self._inlet_nodes_id,
                                             self._outlet_nodes_id, self._component_data)
        except ComponentError:
            msg = f"Fail to build the component {self.get_id()}."
            raise BuildError(msg)

    def get_id(self) -> int:
        return self._id

    def add_inlet_node(self, inlet_pos: int, node_id: int) -> None:
        """Add inlet node to the component in the position specified (first position = 0).

        :raise BuildWarning
        """
        if inlet_pos >= len(self._inlet_nodes_id):
            msg = f"Component {self.get_id()} has only {len(self._inlet_nodes_id)} inlet nodes and can add a node in " \
                  f"the position {inlet_pos}."
            log.warning(msg)
            raise BuildWarning(msg)
        if node_id in self._outlet_nodes_id:
            self._inlet_nodes_id[inlet_pos] = node_id
            msg = f"The node {node_id} is already attached to outlet nodes of the component {self.get_id()}."
            log.warning(msg)
            raise BuildWarning(msg)
        elif node_id in self._inlet_nodes_id:
            msg = f"The node {node_id} is already attached to inlet nodes of the component {self.get_id()}."
            log.warning(msg)
            raise BuildWarning(msg)
        else:
            self._inlet_nodes_id[inlet_pos] = node_id

    def remove_inlet_node(self, inlet_pos: int) -> None:
        """Remove node from an inlet position (first position = 0). To remove node using node_id use remove_node.

        :raise BuildWarning
        """
        try:
            self._inlet_nodes_id[inlet_pos] = None
        except IndexError:
            msg = f"Component {self.get_id()} has only {len(self._inlet_nodes_id)} inlet nodes and can remove a node " \
                  f"in the position {inlet_pos}."
            log.warning(msg)
            raise BuildWarning(msg)

    def add_outlet_node(self, outlet_pos: int, node_id: int) -> None:
        """Add outlet node to the component in the position specified (first position = 0).

        :raise BuildWarning
        """
        if outlet_pos >= len(self._outlet_nodes_id):
            msg = f"Component {self.get_id()} has only {len(self._inlet_nodes_id)} outlet nodes and can add a node in" \
                  f" the position {outlet_pos}."
            log.warning(msg)
            raise BuildWarning(msg)
        if node_id in self._inlet_nodes_id:
            self._outlet_nodes_id[outlet_pos] = node_id
            msg = f"The node {node_id} is already attached to inlet nodes of the component {self.get_id()}."
            log.warning(msg)
            raise BuildWarning(msg)
        elif node_id in self._outlet_nodes_id:
            msg = f"The node {node_id} is already attached to outlet nodes of the component {self.get_id()}."
            log.warning(msg)
            raise BuildWarning(msg)
        else:
            self._outlet_nodes_id[outlet_pos] = node_id

    def remove_outlet_node(self, outlet_pos: int) -> None:
        """Remove node from an outlet position (first position = 0). To remove node using node_id use remove_node.

        :raise BuildWarning
        """
        try:
            self._outlet_nodes_id[outlet_pos] = None
        except IndexError:
            msg = f"Component {self.get_id()} has only {len(self._outlet_nodes_id)} outlet nodes and can remove a " \
                  f"node in the position {outlet_pos}."
            log.warning(msg)
            raise BuildWarning(msg)

    def get_outlet_nodes(self) -> List[int]:
        # Return a list of outlet nodes id attached to component
        return self._outlet_nodes_id

    def remove_node(self, node_id: int) -> None:
        """
        :raise BuildWarning
        """
        if node_id in self._inlet_nodes_id:
            index = self._inlet_nodes_id.index(node_id)
            self._inlet_nodes_id[index] = None
        elif node_id in self._outlet_nodes_id:
            index = self._outlet_nodes_id.index(node_id)
            self._outlet_nodes_id[index] = None
        else:
            msg = f"The node {node_id} is not attached to component {self.get_id()}."
            log.warning(msg)
            raise BuildWarning(msg)

    def get_attached_nodes(self) -> List[int]:
        return self._inlet_nodes_id + self._outlet_nodes_id

    def has_node(self, node_id: int) -> bool:
        return (node_id in self._inlet_nodes_id) or (node_id in self._outlet_nodes_id)

    def set_attribute(self, attribute_name: str, value: float) -> None:
        """
        :raise BuildWarning
        """
        if attribute_name in self._component_info.get_properties():
            cmp_property = self._component_info.get_property(attribute_name)
            if cmp_property.is_correct(value):
                self._component_data[attribute_name] = value
            else:
                component_key = self._component_info.get_component_key()
                msg = f"Component {self.get_id()}, type {component_key}, the {attribute_name} can't be {str(value)}."
                log.warning(msg)
                raise BuildWarning(msg)
        else:
            component_key = self._component_info.get_component_key()
            msg = f"Component {self.get_id()}, type {component_key} doesn't have the attribute {attribute_name}."
            log.warning(msg)
            raise BuildWarning(msg)

    def remove_attribute(self, attribute_name: str) -> None:
        """
        :raise BuildWarning
        """
        if attribute_name in self._component_data:
            del self._component_data[attribute_name]
        else:
            msg = f"Component {self.get_id()} doesn't have {attribute_name}."
            log.warning(msg)
            raise BuildWarning(msg)

    def get_component_type(self) -> 'ComponentInfo':
        return self._component_type.get()


class ComponentFactory(metaclass=Singleton):
    """Factory for Component."""
    def __init__(self):
        self._components = {}

    def add(self, key: str, component_class: Component) -> None:
        """Allows to specify more keys than component class type to retrieve the info.

        :raise ComponentError
        """
        if key in self._components:
            # Check if we are wanting to register the same class. If it is the case, we don't raise an error due to
            # duplicated key.
            mod_spec = inspect.getmodule(component_class).__spec__
            if not mod_spec.has_location:
                msg = f"The module of the class {key} has not location."
                log.error(msg)
                raise ComponentError(msg)

            keyed_cls = self._components[key]

            if not (mod_spec.origin == inspect.getmodule(
                    keyed_cls).__spec__.origin and component_class.__name__ == keyed_cls.__name__):
                msg = f"Key {key} has already been registered in  {type(self)}."
                log.error(msg)
                raise ComponentError(msg)
        else:
            if component_class in self._components:
                msg = f"Class { component_class} has already been registered in {self.__class__}."
                log.error(msg)
                raise ValueError(msg)
            self._components[component_class] = component_class
            self._components[key] = component_class

    def create(self, key: str, *args: Tuple) -> Component:
        """
        :raise ComponentError
        """

        if key not in self._components:
            msg = f"Key {key} is not a registered key in {type(self)}."
            log.error(msg)
            raise ComponentError(msg)

        return self._components[key](*args)


class ComponentInfo:
    """
        Information of the component.

        All information about the components is store in this class: types of components, their properties, name,
        version,...

        Components type supported are:
            - COMPRESSOR: only one stage stage compressor.
            - CONDENSER
            - EVAPORATOR
            - EXPANSION_VALVE
            - MIXER_FLOW: mixing flow components, for example a T. Only with 1 outlet but with  N>1 inlets.
            - PIPING: piping and piping components.
            - SEPARATOR_FLOW: separating flow components, for example a T. With N>1 outlets but only 1 inlet.
            - TWO_INLET_HEAT_EXCHANGER

        Only supported units in SI.
        """
    # Main types
    COMPRESSOR = 'compressor'
    EXPANSION_VALVE = 'expansion_valve'
    CONDENSER = 'condenser'
    EVAPORATOR = 'evaporator'
    MIXER_FLOW = 'mixer_flow'
    SEPARATOR_FLOW = 'separator_flow'
    TWO_INLET_HEAT_EXCHANGER = 'two_inlet_heat_exchanger'
    PIPING = 'piping'

    def __init__(self, component_key: str, component_class: Component, component_type: str, component_version: int =1,
                 updater_data_func: Callable =None, inlet_nodes: int =1, outlet_nodes: int =1):
        self._component_key = component_key
        self._component_class = component_class
        self._component_type = component_type
        self._parent_component_class = inspect.getmro(component_class)[1]  # Parent class
        self._component_version = component_version
        self._updater_data_func = updater_data_func
        self._inlet_nodes = inlet_nodes
        self._outlet_nodes = outlet_nodes
        # Properties info
        self._basic_properties_info = {}
        self._auxiliary_properties_info = {}

    def _add_property(self, dict_to_save: Dict, property_name: str, property_value: NumericProperty):
        """
        :raise InfoError: if property_name is already registered.
        """
        if property_name in self._basic_properties_info or property_name in self._auxiliary_properties_info:
            msg = f"PropertyName {property_name} has already been registered in {type(self)}"
            log.error(msg)
            raise InfoError(msg)

        dict_to_save[property_name] = property_value

    def add_basic_property(self, property_name: str, property_value: NumericProperty):
        self._add_property(self._basic_properties_info, property_name, property_value)

    def add_auxiliary_property(self, property_name: str, property_value: NumericProperty):
        self._add_property(self._auxiliary_properties_info, property_name, property_value)

    def get_basic_properties(self) -> Dict[str, NumericProperty]:
        return self._basic_properties_info

    def get_auxiliary_properties(self) -> Dict[str, NumericProperty]:
        return self._auxiliary_properties_info

    def get_property(self, property_name: str) -> NumericProperty:
        """
        :raise InfoError
        """
        properties = self.get_properties()
        if property_name in properties:
            return properties[property_name]
        else:
            msg = f"PropertyName {property_name} isn't possible in {type(self)}"
            log.error(msg)
            raise InfoError(msg)

    def get_properties(self) -> Dict[str, NumericProperty]:
        return {**self.get_basic_properties(), **self.get_auxiliary_properties()}

    def get_updater_data_func(self) -> Callable:
        return self._updater_data_func

    def get_version(self) -> int:
        return self._component_version

    # Deleted if components of various manufacturers are supported by default.
    # def get_parent_component_class(self):
    #     # Return the parent class. DO NOT WORK with multiple inheritance
    #     return inspect.getmro(self._component_class)[1]

    def get_component_class(self) -> Component:
        return self._component_class

    def get_component_key(self) -> str:
        return self._component_key

    def get_component_type(self) -> str:
        return self._component_type

    def get_inlet_nodes(self) -> int:
        return self._inlet_nodes

    def get_outlet_nodes(self) -> int:
        return self._outlet_nodes


class ComponentInfoFactory(metaclass=Singleton):
    """Factory for ComponentInfo."""
    def __init__(self) -> None:
        self._components_info = {}

    def add(self, component_info: ComponentInfo) -> None:
        """ Allows to specify more keys than component class type to retrieve the info.

        :raise InfoFactoryError
        """
        component_class = component_info.get_component_class()
        key = component_info.get_component_key()
        if key in self._components_info:
            # Check if we are wanting to register the same class. If it is the case, we don't raise an error due to
            # duplicated key.
            mod_spec = inspect.getmodule(component_class).__spec__
            if not mod_spec.has_location:
                msg = f"The module of the class {key} has not location."
                log.error(msg)
                raise InfoFactoryError(msg)

            keyed_cls = self.get(key).get_component_class()

            if not (mod_spec.origin == inspect.getmodule(
                    keyed_cls).__spec__.origin and component_class.__name__ == keyed_cls.__name__):
                msg = f"Key {key} has already been registered in {type(self)}"
                log.error(msg)
                raise InfoFactoryError(msg)
        else:
            if component_class in self._components_info:
                msg = f"Class {component_class} has already been registered in {self.__class__}."
                log.error(msg)
                raise InfoFactoryError(msg)
            self._components_info[component_class] = component_info
            self._components_info[key] = component_info

    def get(self, key: Union[str, object]):
        """
        Return the ComponentInfo registered for a specific key.

        :param key: must be a string, type or a instance of Component class. In this case, the class name will be used
                    as key.
        :raise InfoFactoryError
        """
        if isinstance(key, Component):
            key = key.__class__

        if key in self._components_info:
            return self._components_info[key]
        else:
            msg = f"Key {str(key)} is not a registered key in {str(type(self))}"
            log.error(msg)
            raise InfoFactoryError(msg)

    def get_registered_components(self) -> Dict:
        return self._components_info
