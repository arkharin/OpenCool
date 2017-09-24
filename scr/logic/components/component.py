# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class component.
"""
import inspect
from abc import ABC
from scr.helpers.properties import StrRestricted
from scr.logic.base_classes import Element
from scr.logic.errors import ComponentBuilderError, DeserializerError, PropertyNameError
from scr.logic.warnings import ComponentBuilderWarning, ComponentWarning
from importlib import import_module
from scr.helpers.singleton import Singleton

''' Decorators to use in component plugins to register them in ComponentFactory and ComponentInfoFactory '''


# See question 5929107 (python decorators with parameters) in stackoverflow
# See question 2366713 (Can a Python decorator of an instance method access the class?) in StackOverflow to know about
# how to solve the problem that method decorators are called when class doesn't exist yet. I implemented the same
# solution used by flask-classy. Be aware that methods in classes are bounded functions and therefore points to closure
# variables and are share between instances


def component(key, component_type, version=1, updater_data_func=None, inlet_nodes=1, outlet_nodes=1):
    def real_decorator(cls):
        """ updater_data_func is only required if version is bigger than 1"""
        if not issubclass(cls, Component):
            raise ValueError('This decorator can be use only to decorate components subclasses')

        if version != 1 and updater_data_func is None:
            raise ValueError('updater_func must be distinct to None if version is not one')

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
                    raise ValueError('_property_type unknown')

        ComponentInfoFactory().add(cmp_info)
        ComponentFactory().add(key, cls)

        return cls

    return real_decorator


def fundamental_equation():
    def real_decorator(func):
        setattr(func, '_property_type', 'fundamental')
        return func

    return real_decorator


def basic_property(**kwargs):
    def real_decorator(func):
        if len(kwargs) != 1:
            raise ValueError('basic_property decorator must be called with one keyword argument that it will be the '
                             'property name')
        # Because we are lazy. It's the fastest way to have the key and value. Only iterate one time
        for property_name, value in kwargs.items():
            setattr(func, '_property_name', property_name)
            setattr(func, '_property_type', 'basic')
            setattr(func, '_property_value', value)

        return func

    return real_decorator


def auxiliary_property(**kwargs):
    def real_decorator(func):
        if len(kwargs) != 1:
            raise ValueError('auxiliary_property decorator must be called with one keyword argument that it will be the'
                             ' property name')
        # Because we are lazy. It's the fastest way to have the key and value. Only iterate one time
        for property_name, value in kwargs.items():
            setattr(func, '_property_name', property_name)
            setattr(func, '_property_type', 'auxiliary')
            setattr(func, '_property_value', value)

        return func

    return real_decorator


''' End of the decorators to use in component plugins to register them in ComponentFactory and ComponentInfoFactory '''


class Component(ABC, Element):
    # Arbritary value to check used to check if super method is called in _register_xxx_property_eq() methods
    # TODO pasar a component info
    # Main types
    COMPRESSOR = 'compressor'
    EXPANSION_VALVE = 'expansion_valve'
    CONDENSER = 'condenser'
    EVAPORATOR = 'evaporator'
    MIXER_FLOW = 'mixer_flow'  # N outlets but only 1 inlet
    SEPARATOR_FLOW = 'separator_flow'  # Only 1 outlet and N inlets
    TWO_INLET_HEAT_EXCHANGER = 'two_inlet_heat_exchanger'
    OTHER = 'other'

    def __init__(self, name, id_, inlet_nodes_id, outlet_nodes_id, component_data):

        super().__init__(name, id_)

        self._inlet_nodes = inlet_nodes_id
        self._outlet_nodes = outlet_nodes_id
        self._basic_properties = {}
        self._auxiliary_properties = {}
        self._basic_properties_results = {}
        self._auxiliary_properties_results = {}

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
                        raise ValueError('Property %s has already been defined', property_name)

                    if attribute._property_type == 'basic':
                        self._basic_eqs[property_name] = attribute
                    elif attribute._property_type == 'auxiliary':
                        self._auxiliary_eqs[property_name] = attribute
                    else:
                        raise ValueError('_property_type unknown')

                elif attribute._property_type == 'fundamental':
                    self._fundamental_eqs.append(attribute)
                else:
                    raise ValueError('_property_type unknown')

        for property_name, property_value in component_data.items():
            if hasattr(self, property_name):
                setattr(self, property_name, property_value)
                if property_name in self._basic_eqs:
                    self._basic_properties[property_name] = property_value
                elif property_name in self._auxiliary_eqs:
                    self._auxiliary_properties[property_name] = property_value
                else:
                    raise ValueError('_property_type unknown')
            else:
                raise ValueError('Property name unknown')

    def configure(self, nodes_dict):
        nodes_id = self._inlet_nodes
        self._inlet_nodes = {}
        for node_id in nodes_id:
            self._inlet_nodes[node_id] = nodes_dict[node_id]
        nodes_id = self._outlet_nodes
        self._outlet_nodes = {}
        for node_id in nodes_id:
            self._outlet_nodes[node_id] = nodes_dict[node_id]

    def eval_equations(self):
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

    def solve_property(self, key):
        if key in self.get_basic_properties():
            self._basic_properties_results[key] = self._basic_eqs[key]()
        elif key in self.get_auxiliary_properties():
            self._auxiliary_properties_results[key] = self._auxiliary_eqs[key]()
        else:
            raise ComponentWarning('%s property is not allowed in %s component' % (key, self.get_component_info().
                                                                                   get_component_type()))

    # General methods:
    def get_basic_properties(self):
        # Return an array of dictionaries. Each dictionary in the format of example output components to interface.
        return self._basic_properties

    def get_basic_properties_results(self):
        # Return an array of dictionaries. Each dictionary in the format of example output components to interface.
        return self._basic_properties_results

    def get_auxiliary_properties(self):
        # Return an array of dictionaries. Each dictionary in the format of example output components to interface.
        return self._auxiliary_properties

    def get_auxiliary_properties_results(self):
        # Return an array of dictionaries. Each dictionary in the format of example output components to interface.
        return self._auxiliary_properties_results

    def get_property(self, key):
        return getattr(self, key)

    def get_inlet_nodes(self):
        """
        Return a dictionary of all inlet nodes of the component, keys ordered by lowest to higher pressure.
        For example, first node of two stage compressor is the suction). Equally pressure without specific order.
        """
        return self._inlet_nodes

    def get_id_inlet_nodes(self):
        return list(self.get_inlet_nodes().keys())

    def get_inlet_node(self, id_node):
        return self.get_inlet_nodes()[id_node]

    def get_nodes(self):
        # Return a dictionary with all nodes connected with the component. First inlet nodes.
        return {**self.get_inlet_nodes(), **self.get_outlet_nodes()}

    def get_node(self, id_node):
        return self.get_nodes()[id_node]

    def get_outlet_nodes(self):
        # Return nodes in the same order criterion of get_inlet_nodes
        return self._outlet_nodes

    def get_outlet_node(self, id_node):
        return self.get_outlet_nodes()[id_node]

    def get_id_outlet_nodes(self):
        # Return a list of all outlet nodes of the component
        return list(self.get_outlet_nodes().keys())

    def get_component_info(self):
        return ComponentInfoFactory().get(self)


class AComponentSerializer(ABC):
    # Parameters
    BASIC_PROPERTIES = 'basic properties'
    BASIC_PROPERTIES_CALCULATED = 'basic properties calculate'
    COMPONENTS = 'components'
    COMPONENT_TYPE = 'type'
    IDENTIFIER = 'id'
    INLET_NODES = 'inlet nodes'
    NAME = 'name'
    NODES = 'nodes'
    AUXILIARY_PROPERTIES = 'auxiliary properties'
    AUXILIARY_PROPERTIES_CALCULATED = 'auxiliary properties calculate'
    OUTLET_NODES = 'outlet nodes'
    VERSION = 'version'

    def __init__(self):
        pass

    def deserialize(self, component_file):
        cmp_data = component_file
        cmp = ComponentBuilder(cmp_data[self.IDENTIFIER], cmp_data[self.COMPONENT_TYPE])
        cmp_version = cmp_data[self.VERSION]
        cmp_info = ComponentInfoFactory().get(cmp.get_component_type())
        component_version = cmp_info.get_version()
        if cmp_version < component_version:
            cmp_data = cmp_info.get_updater_data_func(cmp_data, cmp_version)
        elif cmp_version > component_version:
            raise DeserializerError('The version of component ' + self.IDENTIFIER +
                                    ' is greater than component in library. Version ' + str(cmp_version) + ' vs ' +
                                    str(component_version))
        cmp.set_name(cmp_data[self.NAME])
        i = 0
        for node_id in cmp_data[self.INLET_NODES]:
            cmp.add_inlet_node(i, node_id)
            i += 1
        i = 0
        for node_id in cmp_data[self.OUTLET_NODES]:
            cmp.add_outlet_node(i, node_id)
            i += 1
        for key in cmp_data[self.BASIC_PROPERTIES]:
            cmp.set_attribute(key, cmp_data[self.BASIC_PROPERTIES][key])
        for key in cmp_data[self.AUXILIARY_PROPERTIES]:
            cmp.set_attribute(key, cmp_data[self.AUXILIARY_PROPERTIES][key])

        return cmp

    def serialize(self, component):
        cmp_serialized = {self.NAME: component.get_name(), self.IDENTIFIER: component.get_id()}
        cmp_serialized[self.VERSION] = component.get_component_info().get_version()
        cmp_serialized[self.COMPONENT_TYPE] = component.get_component_info().get_component_key()
        cmp_serialized[self.INLET_NODES] = component.get_id_inlet_nodes()
        cmp_serialized[self.OUTLET_NODES] = component.get_id_outlet_nodes()
        self._serialize_properties(cmp_serialized, self.BASIC_PROPERTIES, component.get_basic_properties())
        self._serialize_properties(cmp_serialized, self.BASIC_PROPERTIES_CALCULATED,
                                   component.get_basic_properties_results())
        self._serialize_properties(cmp_serialized, self.AUXILIARY_PROPERTIES,
                                   component.get_auxiliary_properties())
        self._serialize_properties(cmp_serialized, self.AUXILIARY_PROPERTIES_CALCULATED,
                                   component.get_auxiliary_properties_results())
        return cmp_serialized

    def _serialize_properties(self, cmp_serialized, properties_type, properties):
        cmp_serialized[properties_type] = {}
        for i in properties:
            cmp_serialized[properties_type][i] = properties[i]


class ComponentBuilder:
    def __init__(self, id_, component_type):
        self._name = None
        self._id = id_
        self._component_type = StrRestricted(component_type)
        self._component_data = {}
        self._component_info = ComponentInfoFactory().get(self.get_component_type())
        self._inlet_nodes_id = [None] * self._component_info.get_inlet_nodes()
        self._outlet_nodes_id = [None] * self._component_info.get_outlet_nodes()

    def build(self):
        # Build the component
        if self._name is None:
            raise ComponentBuilderWarning('Component %s has no name', self.get_id())
        # Check that all nodes are connected
        if None in self._inlet_nodes_id:
            raise ComponentBuilderError('Missing nodes attached to the inlet of the component %s.', self.get_id())

        if None in self._outlet_nodes_id:
            raise ComponentBuilderError('Missing nodes attached to the outlet of the component %s.', self.get_id())

        return ComponentFactory().create(self.get_component_type(), self._name, self._id, self._inlet_nodes_id,
                                         self._outlet_nodes_id, self._component_data)

    def set_name(self, name):
        self._name = StrRestricted(name)

    def get_id(self):
        return self._id

    def add_inlet_node(self, inlet_pos, node_id):
        if inlet_pos >= len(self._inlet_nodes_id):
            raise ComponentBuilderError('Component with id ' + self.get_id() + ' has only ' +
                                        str(len(self._inlet_nodes_id)) + ' inlet nodes')
        if node_id in self._outlet_nodes_id:
            self._inlet_nodes_id[inlet_pos] = node_id
            raise ComponentBuilderWarning('This node is already attached to outlet nodes')
        elif node_id in self._inlet_nodes_id:
            raise ComponentBuilderWarning('This node is already attached to inlet nodes')
        else:
            self._inlet_nodes_id[inlet_pos] = node_id

    def remove_inlet_node(self, inlet_pos):
        # Remove node from an inlet position. To remove node using node_id use remove_node.
        self._inlet_nodes_id[inlet_pos] = None

    def add_outlet_node(self, outlet_pos, node_id):
        if outlet_pos >= len(self._outlet_nodes_id):
            raise ComponentBuilderError('Component with id ' + self.get_id() + ' has only ' +
                                        str(len(self._outlet_nodes_id)) + ' outlet nodes')
        if node_id in self._inlet_nodes_id:
            self._outlet_nodes_id[outlet_pos] = node_id
            raise ComponentBuilderWarning('This node is already attached to inlet nodes')
        elif node_id in self._outlet_nodes_id:
            raise ComponentBuilderWarning('This node is already attached to outlet nodes')
        else:
            self._outlet_nodes_id[outlet_pos] = node_id

    def remove_outlet_node(self, outlet_pos):
        # Remove node from an outlet position. To remove node using node_id use remove_node.
        self._outlet_nodes_id[outlet_pos] = None

    def get_outlet_nodes(self):
        # Return a list of outlet nodes id attached to component
        return self._outlet_nodes_id

    def remove_node(self, node_id):
        # Remove node from component.
        if node_id in self._inlet_nodes_id:
            index = self._inlet_nodes_id.index(node_id)
            self._inlet_nodes_id[index] = None
        elif node_id in self._outlet_nodes_id:
            index = self._outlet_nodes_id.index(node_id)
            self._outlet_nodes_id[index] = None
        else:
            raise ComponentBuilderWarning('This node is not attached to component')

    def get_attached_nodes(self):
        # Return a list of nodes id attached to component
        return self._inlet_nodes_id + self._outlet_nodes_id

    def has_node(self, node_id):
        return (node_id in self._inlet_nodes_id) or (node_id in self._outlet_nodes_id)

    def set_attribute(self, attribute_name, value):
        if attribute_name in self._component_info.get_properties():
            cmp_property = self._component_info.get_property(attribute_name)
            if cmp_property.is_correct(value):
                self._component_data[attribute_name] = value
            else:
                component_key = self._component_info.get_component_key()
                raise ComponentBuilderError('In ' + component_key + ', ' + attribute_name + ' can\'t be ' + str(value))

    def remove_attribute(self, attribute_name):
        if attribute_name in self._component_data:
            del self._component_data[attribute_name]
        else:
            raise ComponentBuilderWarning('Component ' + self._id + 'doesn\'t have' + str(attribute_name))

    def get_component_type(self):
        return self._component_type.get()


class ComponentFactory(metaclass=Singleton):
    def __init__(self):
        self._components = {}

    def add(self, key, component_class):
        """ Allows to specify more keys than component class type to retrieve the info"""
        if key in self._components:
            # Check if we are wanting to register the same class. If it is the case, we don't raise an error due to
            # duplicated key.
            mod_spec = inspect.getmodule(component_class).__spec__
            if not mod_spec.has_location:
                raise ValueError('The module of the class ' + key + 'has not location')

            keyed_cls = self._components[key]

            if not (mod_spec.origin == inspect.getmodule(
                    keyed_cls).__spec__.origin and component_class.__name__ == keyed_cls.__name__):
                raise ValueError('key' + str(key) + ' has already been registered in ' + str(type(self)))
        else:
            if component_class in self._components:
                raise ValueError('Class %s has already been registered in ', component_class, self.__class__)
            self._components[component_class] = component_class
            self._components[key] = component_class

    def create(self, key, *args):

        if key not in self._components:
            raise ValueError('key' + str(key) + ' doesn\'t is not a registered key in ' + str(type(self)))

        return self._components[key](*args)


class ComponentInfo:
    def __init__(self, component_key, component_class, component_type, component_version=1, updater_data_func=None,
                 inlet_nodes=1, outlet_nodes=1):
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

    def _add_property(self, dict_to_save, property_name, property_value):
        if property_name in self._basic_properties_info or property_name in self._auxiliary_properties_info:
            raise ValueError('Property ' + str(property_name) + ' has already been registered in ' + str(type(self)))

        dict_to_save[property_name] = property_value

    def add_basic_property(self, property_name, property_value):
        self._add_property(self._basic_properties_info, property_name, property_value)

    def add_auxiliary_property(self, property_name, property_value):
        self._add_property(self._auxiliary_properties_info, property_name, property_value)

    def get_basic_properties(self):
        return self._basic_properties_info

    def get_auxiliary_properties(self):
        return self._auxiliary_properties_info

    def get_property(self, property_name):
        properties = self.get_properties()
        if property_name in properties:
            return properties[property_name]
        else:
            raise PropertyNameError('Property ' + str(property_name) + ' is not possible in ' + str(type(self)))

    def get_properties(self):
        return {**self.get_basic_properties(), **self.get_auxiliary_properties()}

    def get_updater_data_func(self):
        return self._updater_data_func

    def get_version(self):
        return self._component_version

    def get_parent_component_class(self):
        # Return the parent class. DO NOT WORK with multiple inheritance
        return inspect.getmro(self._component_class)[1]

    def get_component_class(self):
        return self._component_class

    def get_component_key(self):
        return self._component_key

    def get_component_type(self):
        return self._component_type

    def get_inlet_nodes(self):
        return self._inlet_nodes

    def get_outlet_nodes(self):
        return self._outlet_nodes


class ComponentInfoFactory(metaclass=Singleton):
    def __init__(self):
        self._components_info = {}

    def add(self, component_info):
        """ Allows to specify more keys than component class type to retrieve the info"""
        component_class = component_info.get_component_class()
        key = component_info.get_component_key()
        if key in self._components_info:
            # Check if we are wanting to register the same class. If it is the case, we don't raise an error due to
            # duplicated key.
            mod_spec = inspect.getmodule(component_class).__spec__
            if not mod_spec.has_location:
                raise ValueError('The module of the class ' + key + 'has not location')

            keyed_cls = self.get(key).get_component_class()

            if not (mod_spec.origin == inspect.getmodule(
                    keyed_cls).__spec__.origin and component_class.__name__ == keyed_cls.__name__):
                raise ValueError('key' + str(key) + ' has already been registered in ' + str(type(self)))
        else:
            if component_class in self._components_info:
                raise ValueError('Class %s has already been registered in ', component_class, self.__class__)
            self._components_info[component_class] = component_info
            self._components_info[key] = component_info

    def get(self, key):
        """
        Return the ComponentInfo registered for a specific key.
        Key must be a string, type or a instance of Component class. In this case, the class name will be used as key.
        """
        if isinstance(key, Component):
            key = key.__class__

        if key in self._components_info:
            return self._components_info[key]
        else:
            raise ValueError('key ' + str(key) + ' is not a registered key in ' + str(type(self)))

            # TODO def get_register_components()
