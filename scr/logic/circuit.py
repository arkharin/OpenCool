# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the circuit class
"""

import scr.logic.component as comp
import scr.logic.components.compressor as compressor
import scr.logic.components.condenser as condenser
import scr.logic.components.evaporator as evaporator
import scr.logic.components.expansion_valve as expansion_valve
import scr.logic.errors
import scr.logic.nodes.coolprop_node as cpnode
import scr.logic.refrigerant as ref
from scr.logic.common import GeneralData
from scr.logic.errors import IdDuplicated


class Circuit(GeneralData):
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

    def __init__(self, input_circuit):
        super().__init__(input_circuit[self.NAME], input_circuit[self.IDENTIFIER])
        self._refrigerant = ref.Refrigerant('HEOS', input_circuit[self.REFRIGERANT])
        self._create_nodes(input_circuit)
        self._create_components(input_circuit)
        self._create_mass_flow()

    def _create_mass_flow(self):
        # Only works for 1 inlet for SEPARATOR_FLOW or 1 outlet for MIXER_FLOW
        # Search components that modify flows
        mix_components = self.search_components(comp.Component.MIXER_FLOW)
        separate_components = self.search_components(comp.Component.SEPARATOR_FLOW)
        flow_components = separate_components + mix_components
        # Create and fill id_mass_flow in nodes.
        id_mass_flow = 0
        prior_prior_id_mass_flow = []
        total_id_mass_flow = 1
        if len(flow_components) == 0:
            component = self.get_components()
            keys = list(component.keys())
            component = self.get_component(keys.pop())
            self._fill_id_mass_flow_inlet_nodes(id_mass_flow, prior_prior_id_mass_flow, component, total_id_mass_flow)
        else:
            for component in flow_components:
                component = separate_components[component]
                self._fill_id_mass_flow_inlet_nodes(id_mass_flow, prior_prior_id_mass_flow, component,
                                                    total_id_mass_flow)
        # Created and add to nodes _mass_flows list
        self._mass_flows = [0.0] * (2 * len(separate_components) + 1)
        nodes = self.get_nodes()
        for node in nodes:
            node = nodes[node]
            node.add_mass_flow(self.get_mass_flows())

    def _create_components(self, input_circuit):
        self._components = {}
        for component in input_circuit[self.COMPONENTS]:
            identifier = component[self.IDENTIFIER]
            if identifier in self.get_components():
                raise IdDuplicated("%i is duplicated", identifier)
            name = component[self.NAME]
            component_type = component[self.COMPONENT_TYPE]
            id_nodes = component[self.INLET_NODES]
            inlet_nodes = self._create_list_nodes(id_nodes)
            id_nodes = component[self.OUTLET_NODES]
            outlet_nodes = self._create_list_nodes(id_nodes)
            basic_properties = component[self.BASIC_PROPERTIES]
            optional_properties = component[self.OPTIONAL_PROPERTIES]
            self._components[identifier] = self._construct_component(name, identifier, component_type, inlet_nodes,
                                                                     outlet_nodes, basic_properties,
                                                                     optional_properties)

    def _create_nodes(self, input_circuit):
        self._nodes = {}
        id_nodes = []
        for node in input_circuit[self.NODES]:
            identifier = node[self.IDENTIFIER]
            if identifier in id_nodes:
                raise IdDuplicated("%i is duplicated", identifier)
            else:
                id_nodes.append(identifier)
            name = node[self.NAME]
            refrigerant = self._refrigerant
            self._nodes[identifier] = cpnode.CoolPropHEOSNode(name, identifier, refrigerant)

    def _fill_id_mass_flow_inlet_nodes(self, prior_id_mass_flow, prior_prior_id_mass_flow, component,
                                       total_id_mass_flow):
        # TODO  check if prior_id_mass_flow is not affected by the recurrence
        inlet_nodes = component.get_inlet_nodes()
        outlet_nodes = component.get_outlet_nodes()
        total_next_outlet_nodes = len(outlet_nodes)
        if total_next_outlet_nodes > 1:
            id_mass_flow = prior_prior_id_mass_flow.pop()
        else:
            id_mass_flow = prior_id_mass_flow
        total_nodes = len(inlet_nodes)
        for node in inlet_nodes:
            if total_nodes > 1:
                prior_prior_id_mass_flow.append(prior_id_mass_flow)
                id_mass_flow = total_id_mass_flow
                total_id_mass_flow += 1
            if not node.is_mass_flow_init():
                node.set_id_mass_flow(id_mass_flow)
                next_components = node.get_components_attached()
                for next_component in next_components:
                    self._fill_id_mass_flow_inlet_nodes(id_mass_flow, prior_prior_id_mass_flow, next_component,
                                                        total_id_mass_flow)

    def _create_list_nodes(self, id_nodes):
        nodes = []
        for id_node in id_nodes:
            nodes.append(self.get_node(id_node))
        return nodes

    @staticmethod
    def _construct_component(name, identifier, component_type, inlet_nodes, outlet_nodes, basic_properties,
                             optional_properties):
        # Add new components type here
        if component_type is comp.Component.COMPRESSOR:
            return compressor.Compressor(name, identifier, inlet_nodes, outlet_nodes, basic_properties,
                                         optional_properties)
        elif component_type is comp.Component.CONDENSER:
            return condenser.Condenser(name, identifier, inlet_nodes, outlet_nodes, basic_properties,
                                       optional_properties)
        elif component_type is comp.Component.EVAPORATOR:
            return evaporator.Evaporator(name, identifier, inlet_nodes, outlet_nodes, basic_properties,
                                         optional_properties)
        elif component_type is comp.Component.EXPANSION_VALVE:
            return expansion_valve.ExpansionValve(name, identifier, inlet_nodes, outlet_nodes, basic_properties,
                                                  optional_properties)
        else:
            raise scr.logic.errors.TypeComponentError("Invalid Component. %s is not recognize", component_type)

    def get_component(self, id_component):
        return self._components[id_component]

    def get_components(self):
        return self._components

    def get_mass_flows(self):
        return self._mass_flows

    def get_node(self, id_node):
        return self._nodes[id_node]

    def get_nodes(self):
        return self._nodes

    def get_refrigerant(self):
        return self._refrigerant

    def search_components(self, component_type):
        # Return a list of components with type component_type
        components_found = []
        components = self.get_components()
        for component in components:
            if components[component].get_component_type() is component_type:
                components_found.append(components[component])
        return components_found

    def update_mass_flows(self, mass_flows):
        # input is list of floats
        i = 0
        for mass_flow in mass_flows:
            self.get_mass_flows()[i] = mass_flow
