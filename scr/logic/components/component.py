# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class component.
"""

from abc import ABC, abstractmethod
from scr.logic.common import check_input_str, check_type, check_input_float
from scr.logic.restricted_inputs import StrRestricted
from scr.logic.base_classes import Element
from scr.logic.errors import TypeValueError, PropertyNameError, BuildError, ComponentBuilderError
from scr.logic.warnings import ComponentBuilderWarning
from importlib import import_module


class Component(ABC, Element):
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

    def __init__(self, name, id_, component_type, inlet_nodes_id, outlet_nodes_id, component_data, n_inlet_nodes, n_outlet_nodes, basic_properties_allowed,
                 optional_properties_allowed):

        super().__init__(name, id_)

        self._component_library = component_type
        self._component_type = component_type.rsplit('.')[0]
        self._inlet_nodes = inlet_nodes_id
        self._outlet_nodes = outlet_nodes_id
        self._basic_properties = {x: component_data[x] for x in basic_properties_allowed if x in component_data}
        self._optional_properties = {x: component_data[x] for x in optional_properties_allowed if x in component_data}
        self._basic_properties_results = self.NO_INIT
        self._optional_properties_results = self.NO_INIT

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
    def _calculated_result(self, key):
        # Return a list with length 2. In first position the name of the property calculated and in the second de value.
        # Return None if is empty
        pass

    def calculated_basic_properties(self):
        self._basic_properties_results = self._calculate_properties(self.get_basic_properties())

    def calculated_optional_properties(self):
        self._optional_properties_results = self._calculate_properties(self.get_optional_properties())

    def _calculate_properties(self, properties):
        # Return a dictionary. Keys are de name of properties calculated and items their values.
        results = {}
        for key in properties:
            results[key] = {self.VALUE: self._calculated_result(key), self.UNIT: self.get_property_unit(key)
                            }
        return results

    def get_property_unit(self, prop):
        if prop in self.basic_properties_allowed:
            return self.basic_properties_allowed[prop][self.UNIT]
        else:
            return self.optional_properties_allowed[prop][self.UNIT]

    def eval_equations(self):
        # Return a matrix of two columns with the calculation result of each side of the equation.
        results = []
        int_eq = self._eval_intrinsic_equations()
        if int_eq is not None:
            results.append(int_eq)
        properties = self.get_basic_properties()
        for key in properties:
            results.append(self._eval_basic_equation(key))
        return results

    @abstractmethod
    def _eval_intrinsic_equations(self):
        pass

    @abstractmethod
    def _eval_basic_equation(self, basic_property):
        pass

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
        Return all inlet nodes of the component, keys ordered by lowest to higher pressure.
        For example, first node of two stage compressor is the suction). Equally pressure without specific order.
        """
        return self._inlet_nodes

    def get_id_inlet_nodes(self):
            return self.get_inlet_nodes().keys()

    def get_inlet_node(self, id_node):
            return self.get_inlet_nodes()[id_node]

    def get_nodes(self):
        # Return all nodes connected with the component. First inlet nodes.
        return {**self.get_inlet_nodes(), **self.get_outlet_nodes()}

    def get_node(self, id_node):
            return self.get_nodes()[id_node]

    def get_outlet_nodes(self):
        # Return nodes in the same order criterion of get_inlet_nodes
        return self._outlet_nodes

    def get_outlet_node(self, id_node):
        return self.get_outlet_nodes()[id_node]

    def get_id_outlet_nodes(self):
        return self.get_outlet_nodes().keys()

    def get_component_library(self):
        return self._component_library

    def serialize(self):
        save_object = {self.NAME: self.get_name(), self.IDENTIFIER: self.get_id()}
        save_object[self.COMPONENT_TYPE] = self.get_component_library()
        save_object[self.INLET_NODES] = list(self.get_id_inlet_nodes())
        save_object[self.OUTLET_NODES] = list(self.get_outlet_nodes())

        save_object[self.BASIC_PROPERTIES] = self.get_basic_properties()
        save_object[self.BASIC_PROPERTIES_CALCULATED] = self.get_basic_properties_results()
        save_object[self.OPTIONAL_PROPERTIES] = self.get_optional_properties()
        save_object[self.OPTIONAL_PROPERTIES_CALCULATED] = self.get_optional_properties_results()
        return save_object


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
        cmp_serialized[component.INLET_NODES] = list(component.get_id_inlet_nodes())
        cmp_serialized[component.OUTLET_NODES] = list(component.get_outlet_nodes())

        cmp_serialized[component.BASIC_PROPERTIES] = component.get_basic_properties()
        cmp_serialized[component.BASIC_PROPERTIES_CALCULATED] = component.get_basic_properties_results()
        cmp_serialized[component.OPTIONAL_PROPERTIES] = component.get_optional_properties()
        cmp_serialized[component.OPTIONAL_PROPERTIES_CALCULATED] = component.get_optional_properties_results()
        return cmp_serialized


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
        return Component.build(self._name, self._id, self._component_type.string, self._inlet_nodes_id, self._outlet_nodes_id, self._component_data)

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
        #TODO revisar si se utiliza
        return (node_id in self._inlet_nodes_id) or (node_id in self._outlet_nodes_id)

    def set_attribute(self, attribute_name, value):
        self._component_data[attribute_name] = value

    def remove_attribute(self, attribute_name):
        if attribute_name in self._component_data:
            del self._component_data[attribute_name]

class ComponentFactory:
    # TODO Crear the factory component class
    pass