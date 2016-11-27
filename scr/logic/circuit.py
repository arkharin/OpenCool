# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the circuit class
"""

import scr.logic.components.component as cmp
import scr.logic.nodes.node as nd
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
    REF_LIB = 'refrigerant_library'

    def __init__(self, input_circuit):
        super().__init__(input_circuit[self.NAME], input_circuit[self.IDENTIFIER])
        self._ref_lib = input_circuit[self.REF_LIB]
        self._refrigerant = ref.Refrigerant.build(self.get_ref_lib(), input_circuit[self.REFRIGERANT])
        self._nodes = {}
        self._nodes = self._load_nodes(input_circuit, self.get_ref_lib())
        self._components = {}
        self._components = self._load_components(input_circuit)
        # Information that is generated from nodes and components every time
        self._mass_flows = self._create_mass_flows()
        self._link_nodes_mass_flows()

    def _create_mass_flows(self):
        separate_components = self.search_components_by_type(cmp.Component.SEPARATOR_FLOW)
        return [0.0] * (2 * len(separate_components) + 1)

    def _link_nodes_mass_flows(self):
        # TODO Only works for 1 inlet for SEPARATOR_FLOW or 1 outlet for MIXER_FLOW.
        # Search components that modify flows
        mix_components = self.search_components_by_type(cmp.Component.MIXER_FLOW)
        separate_components = self.search_components_by_type(cmp.Component.SEPARATOR_FLOW)
        flow_components = {**separate_components, **mix_components}
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
        # Add to nodes _mass_flows list
        mass_flows = self.get_mass_flows()
        nodes = self.get_nodes()
        for node in nodes:
            node = nodes[node]
            node.add_mass_flow(mass_flows)
        return nodes

    def _load_components(self, input_circuit):
        components = {}
        nodes = self.get_nodes()
        for component in input_circuit[self.COMPONENTS]:
            identifier = component[self.IDENTIFIER]
            if identifier in components:
                raise IdDuplicated("There are components duplicated. Identifier %i is duplicated", identifier)
            components[identifier] = cmp.Component.build(component, nodes)
        return components

    def _load_nodes(self, input_circuit, ref_lib):
        nodes = {}
        refrigerant = self.get_refrigerant()
        for node in input_circuit[self.NODES]:
            identifier = node[self.IDENTIFIER]
            if identifier in nodes:
                raise IdDuplicated("There are nodes duplicated.%i is duplicated", identifier)
            nodes[identifier] = nd.Node.build(node, refrigerant, ref_lib)
        return nodes

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
        for i in inlet_nodes:
            node = inlet_nodes[i]
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

    def get_component(self, id_component):
        return self.get_components()[id_component]

    def get_components(self):
        return self._components

    def get_mass_flows(self):
        return self._mass_flows

    def get_node(self, id_node):
        return self.get_nodes()[id_node]

    def get_nodes(self):
        return self._nodes

    def get_refrigerant(self):
        return self._refrigerant

    def get_ref_lib(self):
        return self._ref_lib

    def search_components_by_type(self, component_type):
        components = self.get_components()
        return {x: components[x] for x in components if components[x].get_type() == component_type}

    def update_mass_flows(self, mass_flows):
        # input is list of floats
        i = 0
        for mass_flow in mass_flows:
            self.get_mass_flows()[i] = mass_flow
            i += 1
