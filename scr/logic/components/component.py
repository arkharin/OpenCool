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
    MIXER_FLOW = 'mix_flow'  # N outlets but only 1 inlet
    SEPARATOR_FLOW = 'separator_flow'  # Only 1 outlet and N inlets
    TWO_INLET_HEAT_EXCHANGER = 'two_inlet_heat_exchanger'
    OTHER = 'other'
    # Parameters
    BASIC_PROPERTIES = 'basic properties'
    COMPONENTS = 'components'
    COMPONENT_TYPE = 'type'
    IDENTIFIER = 'id'
    INLET_NODES = 'inlet nodes'
    NAME = 'name'
    NODES = 'nodes'
    OPTIONAL_PROPERTIES = 'optional properties'
    OUTLET_NODES = 'outlet nodes'
    REFRIGERANT = 'refrigerant'

    def __init__(self, data, circuit_nodes, n_inlet_nodes, n_outlet_nodes, basic_properties_allowed,
                 optional_properties_allowed):

        super().__init__(data[self.NAME], data[self.IDENTIFIER])

        check_input_str(data[self.COMPONENT_TYPE])
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

    def _attach_to_nodes(self):
        nodes = self.get_nodes()
        for node in nodes:
            nodes[node].attach_component(self)

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
                    check_type(input_properties[key], float)
                    check_input_float(input_properties[key], keys_allowed[key]['lower_limit'],
                                      keys_allowed[key]['upper_limit'])
            else:
                raise PropertyNameError(
                    "Invalid property. %s  is not in %s]" % keys_allowed)

    def _check_input_nodes(self, nodes, n_nodes):
        check_type(nodes, list)
        if len(nodes) == n_nodes:
            return
        else:
            raise ValueError('Number of nodes is wrong. %s is not %s' % (len(nodes), n_nodes))

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
            results[key] = self._calculated_result(key)
        return results

    @abstractmethod
    def _eval_equation_error(self, basic_property):
        # Return floats with equation error.
        pass

    def eval_error(self, error):
        # TODO component will return h_calc and h_circuit
        # Input a list of float and return a list with floats append of equations error.
        properties = self.get_basic_properties()
        if len(properties) == 0:
            error.append(self._eval_equation_error(properties))
        else:
            for key in properties:
                error.append(self._eval_equation_error(key))
        return error

    def get_id_input_properties(self):
        # Return a dictview with the names of inputs of properties
        return self._basic_properties.keys()

    def get_basic_property(self, basic_property):
        return self._basic_properties[basic_property]

    def get_basic_properties(self):
        # Return an array of dictionaries. Each dictionary in the format of example output components to interface.
        return self._basic_properties

    def get_optional_property(self, optional_property):
        return self._optional_properties[optional_property]

    def get_optional_properties(self):
        # Return an array of dictionaries. Each dictionary in the format of example output components to interface.
        return self._optional_properties

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
