# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the circuit class
"""

import scr.logic.components.component as cmp
import scr.logic.nodes.node as nd
import scr.logic.refrigerants.refrigerant as ref
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
        self._refrigerant = ref.Refrigerant.build(self.get_refregirrant_library(), input_circuit[self.REFRIGERANT])
        self._nodes = {}
        self._nodes = self._load_nodes(input_circuit, self.get_refregirrant_library())
        self._components = {}
        self._components = self._load_components(input_circuit)
        # Information that is generated from nodes and components every time
        self._mass_flows = self._create_mass_flows()
        self._link_nodes_mass_flows()

    def _create_mass_flows(self):
        separate_components = self.search_components_by_type(cmp.Component.SEPARATOR_FLOW)
        return [0.0] * (2 * len(separate_components) + 1)

    def _link_nodes_mass_flows(self):
        # Search components that modify flows
        mix_components = self.search_components_by_type(cmp.Component.MIXER_FLOW)
        separate_components = self.search_components_by_type(cmp.Component.SEPARATOR_FLOW)
        flow_components = {**separate_components, **mix_components}
        # Create and fill id_mass_flow in nodes.
        if len(flow_components) == 0:
            id_mass_flow = 0
            id_component = self.get_components_id()[0]
            component = self.get_component(id_component)
            id_node = component.get_id_outlet_nodes()[0]
            outlet_node = component.get_outlet_node(id_node)
            self._fill_id_mass_flow_nodes(id_mass_flow, outlet_node, {id_component:component})
        else:
            id_mass_flow = -1
            for id_component in mix_components:
                id_mass_flow += 1
                component = self.get_component(id_component)
                # A mix component only have one outlet
                id_outlet_node = component.get_id_outlet_nodes()[0]
                outlet_node = component.get_outlet_node(id_outlet_node)
                self._fill_id_mass_flow_nodes(id_mass_flow, outlet_node, flow_components)

            for id_component in separate_components:
                component = self.get_component(id_component)
                outlet_nodes = component.get_outlet_nodes()
                for id_node in outlet_nodes:
                    node = component.get_outlet_node(id_node)
                    id_mass_flow += 1
                    self._fill_id_mass_flow_nodes(id_mass_flow, node, flow_components)

        # Add to nodes _mass_flows list
        mass_flows = self.get_mass_flows()
        nodes = self.get_nodes()
        for id_node in nodes:
            node = nodes[id_node]
            node.add_mass_flow(mass_flows)
        return nodes

    def _fill_id_mass_flow_nodes(self, id_mass_flow, node, stop_components):
        while True:
            node.set_id_mass_flow(id_mass_flow)
            # This components only have one outlet because is not a flow component.
            inlet_component = node.get_inlet_components_attached()[0]
            id_inlet_component = inlet_component.get_id()
            if id_inlet_component in stop_components:
                break
            else:
                node = inlet_component.get_outlet_node(inlet_component.get_id_outlet_nodes()[0])

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

    def get_component(self, id_component):
        return self.get_components()[id_component]

    def get_components(self):
        return self._components

    def get_components_id(self):
        return list(self._components.keys())

    def get_mass_flows(self):
        return self._mass_flows

    def get_node(self, id_node):
        return self.get_nodes()[id_node]

    def get_nodes(self):
        return self._nodes

    def get_refrigerant(self):
        return self._refrigerant

    def get_refregirrant_library(self):
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

    def get_save_object(self):
        save_object = {'name': self.get_name()}
        save_object['id'] = self.get_id()

        refrigerant = self.get_refrigerant()
        save_object['refrigerant'] = refrigerant.name()
        save_object['refrigerant_library'] = self.get_refregirrant_library()

        save_object['nodes'] = []
        nodes = self.get_nodes()
        for i in nodes:
            save_object['nodes'].append(nodes[i].get_save_object())

        save_object['components'] = []
        components = self.get_components()
        for i in components:
            save_object['components'].append(components[i].get_save_object())

        return save_object
