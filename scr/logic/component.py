# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class component.
"""

from abc import ABC, abstractmethod
from scr.logic.common import GeneralData, check_input_str, check_type, check_input_float
from scr.logic.errors import TypeValueError, PropertyNameError


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

    def __init__(self, name, identifier, component_type, inlet_nodes, n_inlet_nodes, outlet_nodes, n_outlet_nodes,
                 basic_properties, basic_properties_allowed, optional_properties, optional_properties_allowed):

        super().__init__(name, identifier)

        check_input_str(component_type)
        self._component_type = component_type
        self._check_input_nodes(inlet_nodes, n_inlet_nodes)
        self._inlet_nodes = inlet_nodes

        self._check_input_nodes(outlet_nodes, n_outlet_nodes)
        self._outlet_nodes = outlet_nodes

        self._check_input_properties(basic_properties, basic_properties_allowed)
        self._basic_properties = basic_properties

        self._check_input_properties(optional_properties, optional_properties_allowed)
        self._optional_properties = optional_properties

        self._attach_to_nodes()

        self._basic_properties_results = self.NO_INIT
        self._optional_properties_results = self.NO_INIT

    def _attach_to_nodes(self):
        nodes = self.get_nodes()
        for node in nodes:
            node.attach_component(self)

    @staticmethod
    def _check_input_properties(input_properties, keys_allowed):
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

    @staticmethod
    def _check_input_nodes(nodes, n_nodes):
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
        # Input a list of float and return a list with floats append of equations error.
        properties = self.get_basic_properties()
        if len(properties) == 0:
            error.append(self._eval_equation_error(properties))
        else:
            for key in properties:
                error.append(self._eval_equation_error(key))
        return error

    def get_name_input_properties(self):
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

    def get_component_type(self):
        return self._component_type

    def get_inlet_nodes(self):
        """
        Return array of nodes. Return all inlet nodes of the component, first with the lowest pressure.
        For example, first node of two stage compressor is the suction). Equally pressure without specific order.
        """
        return self._inlet_nodes

    def get_nodes(self):
        # Return array. Return all nodes connected with the component. First inlet nodes.
        return self.get_inlet_nodes() + self.get_outlet_nodes()

    def get_outlet_nodes(self):
        # Return array of nodes in the same order criterion of get_inlet_nodes
        return self._outlet_nodes
