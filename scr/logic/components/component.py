# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class component.
"""

from abc import ABC, abstractmethod
from scr.logic.common import GeneralData, check_input_str, check_type, check_input_float
from scr.logic.errors import TypeValueError, PropertyNameError
from importlib import import_module


class Component(ABC, GeneralData):
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

    def __init__(self, data, circuit_nodes, n_inlet_nodes, n_outlet_nodes, basic_properties_allowed,
                 optional_properties_allowed):

        super().__init__(data[self.NAME], data[self.IDENTIFIER])

        check_type(data[self.COMPONENT_TYPE], str)
        self._component_library = data[self.COMPONENT_TYPE]
        self._component_type = data[self.COMPONENT_TYPE].rsplit('.')[0]

        id_inlet_nodes = data[self.INLET_NODES]
        self._check_input_nodes(id_inlet_nodes, n_inlet_nodes)
        self._inlet_nodes = {x: circuit_nodes[x] for x in id_inlet_nodes}

        id_outlet_nodes = data[self.OUTLET_NODES]
        self._check_input_nodes(id_outlet_nodes, n_outlet_nodes)
        self._outlet_nodes = {x: circuit_nodes[x] for x in id_outlet_nodes}

        self._check_input_properties(data[self.BASIC_PROPERTIES], basic_properties_allowed)
        self._basic_properties = data[self.BASIC_PROPERTIES]

        self._check_input_properties(data[self.OPTIONAL_PROPERTIES], optional_properties_allowed)
        self._optional_properties = data[self.OPTIONAL_PROPERTIES]

        self._attach_to_nodes()

        self._basic_properties_results = self.NO_INIT
        self._optional_properties_results = self.NO_INIT

    @staticmethod
    def build(component, circuit_nodes):
        # Dynamic importing modules
        component_type = component[Component.COMPONENT_TYPE]
        try:
            cmp = import_module('scr.logic.components.' + component_type)
        except ImportError:
            print('Error loading component. Type: %s is not found', component_type)
            exit(1)
        aux = component_type.rsplit('.')
        class_name = aux.pop()
        # Only capitalize the first letter
        class_name = class_name.replace(class_name[0], class_name[0].upper(), 1)
        class_ = getattr(cmp, class_name)
        return class_(component, circuit_nodes)

    # __init__ relate methods:
    def _attach_to_nodes(self):
        for id_node in self.get_inlet_nodes():
            node = self.get_node(id_node)
            node.attach_inlet_component(self)
        for id_node in self.get_outlet_nodes():
            node = self.get_node(id_node)
            node.attach_outlet_component(self)

    def _check_input_properties(self, input_properties, keys_allowed):
        # Keys allow is a dictionary with keys names = name properties and each key with a dictionary with lower_limit
        # and upper_limit keys and values.
        try:
            check_type(input_properties, dict)
        except TypeValueError:
            print('Input properties are not a dictionary!')
            exit(1)

        for key in input_properties:
            if key in keys_allowed:
                    check_type(input_properties[key][self.VALUE], float)
                    check_input_float(input_properties[key][self.VALUE], keys_allowed[key][self.LOWER_LIMIT],
                                      keys_allowed[key][self.UPPER_LIMIT])
                    check_input_str(input_properties[key][self.UNIT], keys_allowed[key][self.UNIT])
            else:
                raise PropertyNameError(
                    "Invalid property. %s  is not in %s]" % keys_allowed)

    def _check_input_nodes(self, nodes, n_nodes):
        check_type(nodes, list)
        if len(nodes) == n_nodes:
            return
        else:
            raise ValueError('Number of nodes is wrong. %s is not %s' % (len(nodes), n_nodes))

    # PostSolver evaluation methods
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
            results[key] = {self.VALUE: self._calculated_result(key), self.UNIT: self.get_property_unit(properties[key])
                            }
        return results

    # Solver evaluation methods:
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
        return self._basic_properties[basic_property][self.VALUE]

    def get_basic_properties(self):
        # Return an array of dictionaries. Each dictionary in the format of example output components to interface.
        return self._basic_properties

    def get_basic_properties_results(self):
        # Return an array of dictionaries. Each dictionary in the format of example output components to interface.
        return self._basic_properties_results

    def get_optional_property(self, optional_property):
        return self._optional_properties[optional_property][self.VALUE]

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

    def get_property_unit(self, prop):
        return prop[self.UNIT]

    def get_save_object(self):
        # Return save object
        save_object = {self.NAME: self.get_name(), self.IDENTIFIER: self.get_id()}
        save_object[self.COMPONENT_TYPE] = self.get_component_library()
        save_object[self.INLET_NODES] = self.get_id_inlet_nodes()
        save_object[self.OUTLET_NODES] = self.get_id_outlet_nodes()

        save_object[self.BASIC_PROPERTIES] = self.get_basic_properties()
        save_object[self.BASIC_PROPERTIES_CALCULATED] = self.get_basic_properties_results()
        save_object[self.OPTIONAL_PROPERTIES] = self.get_optional_properties()
        save_object[self.OPTIONAL_PROPERTIES_CALCULATED] = self.get_optional_properties_results()
        return save_object
