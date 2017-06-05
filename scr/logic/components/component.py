# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class component.
"""
import inspect
from abc import ABC, abstractmethod
from importlib import import_module
from collections import namedtuple

from scr.helpers.properties import StrRestricted
from scr.logic.base_classes import Element
from scr.logic.errors import TypeValueError, PropertyNameError, BuildError, ComponentBuilderError
from scr.logic.warnings import ComponentBuilderWarning, ComponentWarning
from importlib import import_module
from scr.helpers.singleton import Singleton


# TODO new form to evaluated the error need to be implemented.

''' Decorators to use in component plugins to register them in ComponentFactory and ComponentInfoFactory '''
# See question 5929107 (python decorators with parameters) in stackoverflow
# See question 2366713 (Can a Python decorator of an instance method access the class?) in StackOverflow to know about how to
# solve the problem that method decorators are called when class doesn't exist yet. I implemented the same solution
# used by flask-classy. Be aware that methods in classes are bounded functions and therefore points to closure
# variables and are share between instances


def component(keys, version=1, updater_data_func=None):
    def real_decorator(cls):
        """ updater_data_func is only required if version is bigger than 1"""
        if not issubclass(cls, Component):
            raise ValueError('This decorator can be use only to decorate components subclasses')

        if version != 1 and updater_data_func == None:
            raise ValueError('updater_func must be distinct to None if version is not one')

        cmp_info = ComponentInfo(cls, component_version=version, updater_data_func=updater_data_func)

        # Search those functions in the class that has been decorated with *_property decorator and add info in
        # to component info
        for member in vars(cls).values():
            if callable(member) and hasattr(member, '_property_name'):
                if member._propery_type == 'fundamental':
                    cmp_info.add_fundamental_property(member._property_name, member._property_value)
                elif member._propery_type == 'basic':
                    cmp_info.add_basic_property(member._property_name, member._property_value)
                elif member._propery_type == 'extended':
                    cmp_info.add_extended_property(member._property_name, member._property_value)
                else:
                    raise ValueError('_propery_type unknown')

        ComponentInfoFactory().add(cmp_info, keys)
        ComponentFactory().add(cls, keys)

        return cls
    return real_decorator


def fundamental_property(**kwargs):
    def real_decorator(func):
        if len(kwargs) != 1 :
            ValueError('fundamental_property decorator must be called with one keyword argument that it will be the property name')

        for property_name, value in kwargs.items():
            setattr(func, '_property_name', property_name)
            setattr(func, '_propery_type', 'fundamental' )
            setattr(func, '_property_value', value)

        return func
    return real_decorator


def basic_property(**kwargs):
    def real_decorator(func):
        if len(kwargs) != 1 :
            ValueError('basic_property decorator must be called with one keyword argument that it will be the property name')

        for property_name, value in kwargs.items():
            setattr(func, '_property_name', property_name)
            setattr(func, '_propery_type', 'basic' )
            setattr(func, '_property_value', value)

        return func
    return real_decorator


def auxiliary_property(**kwargs):
    def real_decorator(func):
        if len(kwargs) != 1 :
            ValueError('auxiliary_property decorator must be called with one keyword argument that it will be the property name')

        for property_name, value in kwargs.items():
            setattr(func, '_property_name', property_name)
            setattr(func, '_propery_type', 'extended' )
            setattr(func, '_property_value', value)

        return func
    return real_decorator

''' End of the decorators to use in component plugins to register them in ComponentFactory and ComponentInfoFactory '''


class Component(ABC, Element):
    # Arbritary value to check used to check if super method is called in _register_xxx_property_eq() methods
    # FIXME search better name
    NO_INIT = None
    # Main types
    COMPRESSOR = 'compressor'
    EXPANSION_VALVE = 'expansion_valve'
    CONDENSER = 'condenser'
    EVAPORATOR = 'evaporator'
    MIXER_FLOW = 'mixer_flow'  # N outlets but only 1 inlet
    SEPARATOR_FLOW = 'separator_flow'  # Only 1 outlet and N inlets
    TWO_INLET_HEAT_EXCHANGER = 'two_inlet_heat_exchanger'
    OTHER = 'other'
    # Parameters
    BASIC_PROPERTIES = 'basic properties'
    BASIC_PROPERTIES_CALCULATED = 'basic properties calculate'
    COMPONENTS = 'components'
    COMPONENT_TYPE = 'type'
    IDENTIFIER = 'id'
    INLET_NODES = 'inlet nodes'
    NAME = 'name'
    NODES = 'nodes'
    OPTIONAL_PROPERTIES = 'optional properties'
    OPTIONAL_PROPERTIES_CALCULATED = 'optional properties calculate'
    OUTLET_NODES = 'outlet nodes'
    REFRIGERANT = 'refrigerant'
    VALUE = 'value'
    UNIT = 'unit'
    LOWER_LIMIT = 'lower_limit'
    UPPER_LIMIT = 'upper_limit'

    def __init__(self, name, id_, component_type, inlet_nodes_id, outlet_nodes_id, component_data, n_inlet_nodes, n_outlet_nodes, basic_properties_allowed,
                 optional_properties_allowed):

        super().__init__(name, id_)

        self._component_library = component_type
        self._component_type = component_type.rsplit('.')[0]
        self._inlet_nodes = inlet_nodes_id
        self._outlet_nodes = outlet_nodes_id
        # TODO at this moment, is used. Fix in the future
        self._basic_properties = {x: component_data[x] for x in basic_properties_allowed if x in component_data}
        self._optional_properties = {x: component_data[x] for x in optional_properties_allowed if x in component_data}
        self._basic_properties_results = {}
        self._optional_properties_results = {}

        # Create and register the properties
        self._fundamental_eqs = {}
        self._basic_eqs = {}
        self._extended_eqs = {}

        # Search those functions in the class that has been decorated with *_property decorator
        # and add equations dictionaries
        for s_attribute in dir(self):
            attribute = getattr(self, s_attribute)
            if callable(attribute) and hasattr(attribute, '_property_name'):
                property_name = attribute._property_name
                if not hasattr(self, property_name):
                    setattr(self, property_name, None)
                else:
                    raise ValueError('Property %s has already been defined', property_name)

                if attribute._propery_type == 'fundamental':
                    self._fundamental_eqs[property_name] = attribute
                elif attribute._propery_type == 'basic':
                    self._basic_eqs[property_name] = attribute
                elif attribute._propery_type == 'extended':
                    self._extended_eqs[property_name] = attribute
                else:
                    raise ValueError('_propery_type unknown')

        for property_name, property_vale in component_data.items():
            if hasattr(self, property_name):
                setattr(self, property_name, property_vale)
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


    @staticmethod
    def build(name, id_, component_type, inlet_nodes_id, outlet_nodes_id, component_data):
        # Dynamic importing modules
        cmp_type = component_type
        try:
            cmp = import_module('scr.logic.components.' + cmp_type)
        except ImportError:
            print('Error loading component. Type: %s is not found', cmp_type)
            exit(1)
        aux = component_type.rsplit('.')
        class_name = aux.pop()
        # Only capitalize the first letter
        class_name = class_name.replace(class_name[0], class_name[0].upper(), 1)
        class_ = getattr(cmp, class_name)
        return class_(name, id_, component_type, inlet_nodes_id, outlet_nodes_id, component_data)

    @abstractmethod
    def calculated_result(self, key):
        # Calculated the result of the key. Return PropertyNameError if key doesn't exist.

        # TODO change to get_property. Problem, now I have get_xxx_properties for the solver and  presolver. Maybe rename for better name.
        # Return a list with length 2. In first position the name of the property calculated and in the second de value.
        # Return None if is empty

        pass

    def add_property_result(self, key, value):
        if key in self.basic_properties_allowed:
            if key in self._basic_properties_results:
                raise ComponentWarning('%s property is already calculated. Value is overwritten' % key)
            self._basic_properties_results[key] = self.calculated_result(key)

        elif key in self.optional_properties_allowed:
            if key in self._optional_properties_results:
                raise ComponentWarning('%s property is already calculated. Value is overwritten' % key)
            self._optional_properties_results[key] = value
        else:
            raise ComponentWarning('%s property is not allowed in %s component' % (key, self.get_type()))

    def get_property_unit(self, prop):
        # TODO future, information will the save in the component. Remove this method.

        if prop in self.basic_properties_allowed:
            return self.basic_properties_allowed[prop][self.UNIT]
        else:
            return self.optional_properties_allowed[prop][self.UNIT]

    def eval_equations(self):
        # Return a matrix of two columns with the calculation result of each side of the equation.
        results = []
        int_eq = self._eval_intrinsic_equations()
        if int_eq is not None:
            for i in int_eq:
                results.append(i)
        properties = self.get_basic_properties()
        for key in properties:
            results.append(self._eval_basic_equation(key))
        return results

    @abstractmethod
    def _eval_intrinsic_equations(self):
        # Return list of list with pairs of the calculations of each side of the equations.
        pass

    @abstractmethod
    def _eval_basic_equation(self, key_basic_property):
        # Return list with the calculations of each side of the equation. Only one equation for each key_basic_property.
        pass

    # General methods:
    def get_id_input_properties(self):
        # Return a dictview with the names of inputs of properties
        return self._basic_properties.keys()

    def get_basic_property(self, basic_property):
        return self._basic_properties[basic_property]

    def get_basic_properties(self):
        # Return an array of dictionaries. Each dictionary in the format of example output components to interface.
        return self._basic_properties

    def get_basic_properties_results(self):
        # Return an array of dictionaries. Each dictionary in the format of example output components to interface.
        return self._basic_properties_results

    def get_optional_property(self, optional_property):
        return self._optional_properties[optional_property]

    def get_optional_properties(self):
        # Return an array of dictionaries. Each dictionary in the format of example output components to interface.
        return self._optional_properties

    def get_optional_properties_results(self):
        # Return an array of dictionaries. Each dictionary in the format of example output components to interface.
        return self._optional_properties_results

    def get_type(self):
        return self._component_type

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

    def get_component_library(self):
        return self._component_library


class AComponentSerializer(ABC):
    NO_INIT = None
    # Main types
    COMPRESSOR = 'compressor'
    EXPANSION_VALVE = 'expansion_valve'
    CONDENSER = 'condenser'
    EVAPORATOR = 'evaporator'
    MIXER_FLOW = 'mix_flow'  # N outlets but only 1 inlet
    SEPARATOR_FLOW = 'separator_flow'  # Only 1 outlet and N inlets
    TWO_INLET_HEAT_EXCHANGER = 'two_inlet_heat_exchanger'
    OTHER = 'other'
    # Parameters
    BASIC_PROPERTIES = 'basic properties'
    BASIC_PROPERTIES_CALCULATED = 'basic properties calculate'
    COMPONENTS = 'components'
    COMPONENT_TYPE = 'type'
    IDENTIFIER = 'id'
    INLET_NODES = 'inlet nodes'
    NAME = 'name'
    NODES = 'nodes'
    OPTIONAL_PROPERTIES = 'optional properties'
    OPTIONAL_PROPERTIES_CALCULATED = 'optional properties calculate'
    OUTLET_NODES = 'outlet nodes'
    REFRIGERANT = 'refrigerant'
    VALUE = 'value'
    UNIT = 'unit'
    LOWER_LIMIT = 'lower_limit'
    UPPER_LIMIT = 'upper_limit'

    def __init__(self):
        pass

    def deserialize(self, component_file):
        cmp = ComponentBuilder(component_file[self.IDENTIFIER], component_file[self.COMPONENT_TYPE])
        cmp.set_name(component_file[self.NAME])
        i = 0
        for node_id in component_file[self.INLET_NODES]:
            cmp.add_inlet_node(i, node_id)
            i += 1
        i = 0
        for node_id in component_file[self.OUTLET_NODES]:
            cmp.add_outlet_node(i, node_id)
            i += 1
        for basic_property in component_file[self.BASIC_PROPERTIES]:
            cmp.set_attribute(basic_property, component_file[self.BASIC_PROPERTIES][basic_property][self.VALUE])
        for optional_property in component_file[self.OPTIONAL_PROPERTIES]:
            cmp.set_attribute(optional_property, component_file[self.OPTIONAL_PROPERTIES][optional_property][self.VALUE])

        return cmp

    def serialize(self, component):
        cmp_serialized = {component.NAME: component.get_name(), component.IDENTIFIER: component.get_id()}
        cmp_serialized[component.COMPONENT_TYPE] = component.get_component_library()
        cmp_serialized[component.INLET_NODES] = component.get_id_inlet_nodes()
        cmp_serialized[component.OUTLET_NODES] = component.get_id_outlet_nodes()
        self._serialize_properties(cmp_serialized, component, self.BASIC_PROPERTIES, component.get_basic_properties())
        self._serialize_properties(cmp_serialized, component, self.BASIC_PROPERTIES_CALCULATED,
                                   component.get_basic_properties_results())
        self._serialize_properties(cmp_serialized, component, self.OPTIONAL_PROPERTIES,
                                   component.get_optional_properties())
        self._serialize_properties(cmp_serialized, component, self.OPTIONAL_PROPERTIES_CALCULATED,
                                   component.get_optional_properties_results())
        return cmp_serialized

    def _serialize_properties(self, cmp_serialized, component, properties_type, properties):
        cmp_serialized[properties_type] = {}
        for i in properties:
            cmp_serialized[properties_type][i] = {self.VALUE: properties[i], self.UNIT: component.get_property_unit(i)}


class ComponentBuilder:
    def __init__(self, id_, component_type):
        self._name = None
        self._id = id_
        self._component_type = StrRestricted(component_type)
        self._component_data = {}

        # TODO This code is temporal. Components must provide information about the inlet and outlet nodes required.
        if component_type == Component.SEPARATOR_FLOW:
            self._inlet_nodes_id = [None] * 1
            self._outlet_nodes_id = [None] * 2
        elif component_type == Component.MIXER_FLOW:
            self._inlet_nodes_id = [None] * 2
            self._outlet_nodes_id = [None] * 1
        else:
            self._inlet_nodes_id = [None] * 1
            self._outlet_nodes_id = [None] * 1

    def build(self):
        # Build the component
        if self._name is None:
            raise ComponentBuilderWarning('Component %s has no name', self.get_id())
        # Check that all nodes are connected
        if None in self._inlet_nodes_id:
            raise ComponentBuilderError('Missing nodes attached to the inlet of the component %s.', self.get_id())

        if None in self._outlet_nodes_id:
            raise ComponentBuilderError('Missing nodes attached to the outlet of the component %s.', self.get_id())

        # TODO check the correctness of the data throw component info retrieved with ComponentFactory
        return Component.build(self._name, self._id, self._component_type.get(), self._inlet_nodes_id, self._outlet_nodes_id, self._component_data)

    def set_name(self, name):
        self._name = StrRestricted(name)

    def get_id(self):
        return self._id

    def add_inlet_node(self, inlet_pos, node_id):
        if node_id in self._outlet_nodes_id:
            self._inlet_nodes_id[inlet_pos] = node_id
            raise ComponentBuilderWarning('This node is already attached to outlet nodes')
        elif node_id in self._inlet_nodes_id:
            raise ComponentBuilderWarning('This node is already attached to inlet nodes')
        else:
            self._inlet_nodes_id[inlet_pos] = node_id

    def remove_inlet_node(self, inlet_pos):
        # Remove node from inlet position
        self._inlet_nodes_id[inlet_pos] = None

    def add_outlet_node(self, outlet_pos, node_id):
        if node_id in self._inlet_nodes_id:
            self._outlet_nodes_id[outlet_pos] = node_id
            raise ComponentBuilderWarning('This node is already attached to inlet nodes')
        elif node_id in self._outlet_nodes_id:
            raise ComponentBuilderWarning('This node is already attached to outlet nodes')
        else:
            self._outlet_nodes_id[outlet_pos] = node_id

    def remove_outlet_node(self, outlet_pos):
        # Remove node from the outlet position
        self._outlet_nodes_id[outlet_pos] = None

    def get_outlet_nodes_id(self):
        # Return a list of outlet nodes id attached to component
        return self._outlet_nodes_id

    def remove_node(self, node_id):
        # Remove node from component.
        if node_id in self._inlet_nodes_id:
            self._inlet_nodes_id.remove(node_id)
        elif node_id in self._outlet_nodes_id:
            self._outlet_nodes_id.remove(node_id)
        else:
            raise ComponentBuilderWarning('This node is not attached to component')

    def get_nodes_id(self):
        # Return a list of nodes id attached to component
        return self._inlet_nodes_id + self._outlet_nodes_id

    def has_node(self, node_id):
        #TODO check if is used
        return (node_id in self._inlet_nodes_id) or (node_id in self._outlet_nodes_id)

    def set_attribute(self, attribute_name, value):
        self._component_data[attribute_name] = value

    def remove_attribute(self, attribute_name):
        if attribute_name in self._component_data:
            del self._component_data[attribute_name]


class ComponentFactory(metaclass=Singleton):
    def __init__(self):
        self._components = {}

    def add(self, component_class, keys=None):
        """ Allows to specify more keys than component class name to retrieve the info"""
        if component_class in self._components:
            raise ValueError('Class %s has already been registered in ', component_class, self.__class__)

        self._components[component_class] = component_class

        if keys is not None:
            try:
                for key in keys:
                    if key in self._components:
                        raise ValueError('key' + str(key) + ' has already been registered in ' + str(type(self)))
                    self._components[key] = component_class
            except TypeError:
                # There are only a key
                if keys in self._components:
                    raise ValueError('key' + str(keys) + ' has already been registered in ' + str(type(self)))
                self._components[keys] = component_class

    def create(self, key, info):

        if key not in self._components:
            raise ValueError('key' + str(key) + ' doesn\'t is not a registered key in ' + str(type(self)))

        return self._components[key](info)


class ComponentInfo:
    def __init__(self, component_class, component_version=1, updater_data_func=None):
        self.component_class = component_class
        self._parent_component_class = inspect.getmro(component_class)[1]  # Parent class
        self._component_version = component_version
        self.updater_data_func = updater_data_func

        # Properties equations
        self._fundamental_properties_info = {}
        self._basic_properties_info = {}
        self._extended_properties_info = {}

    def _add_property(self, dict_to_save, property_name, property_value):

        # TODO check if two properties never have the same name (Altough one is fundamental and the other auxliar)
        if property_name in dict_to_save:
            raise ValueError('Property ' + str(property_name) + ' has already been registered in ' + str(type(self)))

            # PropertyInfo = namedtuple('PropertyInfo','value func_name')
            # dict_to_save[property_name] = PropertyInfo(property_value, property_func_name)
        dict_to_save[property_name] = property_value

    def add_fundamental_property(self, property_name, property_value):
        self._add_property(self._fundamental_properties_info, property_name, property_value)

    def add_basic_property(self, property_name, property_value):
        self._add_property(self._basic_properties_info, property_name, property_value)

    def add_extended_property(self, property_name, property_value):
        self._add_property(self._extended_properties_info, property_name, property_value)

    def get_fundamental_properties(self):
        return self._fundamental_properties_info

    def get_basic_properties(self):
        return self._basic_properties_info

    def get_extended_properties(self):
        return self._extended_properties_info

    def get_properties(self):
        return {**self.get_fundamental_properties(), **self.get_basic_properties(), **self.get_extended_properties()}

    def get_updater_data_func(self):
        return self.updater_data_func

    def get_version(self):
        return self._component_version

    def get_parent_component_class(self):
        # Return the parent class. DO NOT WORK with multiple inheritance
        return inspect.getmro(self.component_class)[1]

    def get_component_class(self):
        return self.component_class


class ComponentInfoFactory(metaclass=Singleton):
    def __init__(self):
        self._components_info = {}

    def add(self, component_info, keys=None):
        """ Allows to specify more keys than component class type to retrieve the info"""
        component_class = component_info.get_component_class()
        if component_class in self._components_info:
            raise ValueError('Class %s has already been registered in ', component_class, self.__class__)

        self._components_info[component_class] = component_info

        if keys is not None:
            try:
                for key in keys:
                    if key in self._components_info:
                        raise ValueError('key' + str(key) + ' has already been registered in ' + str(type(self)))
                    self._components_info[key] = component_info
            except TypeError:
                # There is only one key and it isn't iterable
                if keys in self._components_info:
                    raise ValueError('key' + str(keys) + ' has already been registered in ' + str(type(self)))
                self._components_info[keys] = component_info

    def get(self, key):
        """
        Return the ComponentInfo registered for a specific key. 
            key must be a string, type or a instance of Component class. In this case, the class name will be used as key.  
        """
        if isinstance(key, Component):
            key = key.__class__

        if key in self._components_info:
            return self._components_info[key]
        else:
            raise ValueError('key' + str(key) + ' doesn\'t is not a registered key in ' + str(type(self)))

            # TODO def get_register_components()
