# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the circuit class
"""

import scr.logic.components.component as cmp
import scr.logic.nodes.node as nd
import scr.logic.refrigerants.refrigerant as ref
from scr.logic.base_classes import Element, Identifier
from scr.logic.restricted_inputs import StrRestricted
from scr.logic.errors import IdDuplicatedError, ValuePropertyError, CircuitBuilderError, BuildError
from scr.logic.warnings import CircuitBuilderWarning


class Circuit(Element):
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

    def __init__(self, name, id_, refrigerant, refrigerant_library):
        super().__init__(name, id_)
        self._ref_lib = refrigerant_library
        self._refrigerant = ref.Refrigerant.build(self.get_refrigerant_library(), refrigerant)
        self._nodes = {}
        self._components = {}
        self._mass_flows = []

    def _add_component(self, component_object):
        # Add component object to circuit.
        self._components[component_object.get_id()] = component_object

    def _add_node(self, node_object):
        # Add node object to circuit.
        self._nodes[node_object.get_id()] = node_object

    def configure(self):
        # Configure circuit to solve it later
        self._mass_flows = self._create_mass_flows()
        for node_id in self.get_nodes():
            node = self.get_node(node_id)
            # A list of all mass_flows of te circuit is passes to node. Later, will be configurated which mass flow it
            # is the correct.
            node.configure(self.get_components(), self.get_mass_flows())

        for component_id in self.get_components():
            component = self.get_component(component_id)
            component.configure(self.get_nodes())

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
            self._fill_id_mass_flow_nodes(id_mass_flow, outlet_node, {id_component: component})
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

    def _fill_id_mass_flow_nodes(self, id_mass_flow, node, stop_components):
        while True:
            node.set_id_mass_flow(id_mass_flow)
            # This components only have one outlet because is not a flow component.
            inlet_component = node.get_inlet_component_attached()
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
                raise IdDuplicatedError("There are components duplicated. Identifier %i is duplicated", identifier)
            components[identifier] = cmp.Component.build(component, nodes)
        return components

    def _load_nodes(self, input_circuit, ref_lib):
        nodes = {}
        refrigerant = self.get_refrigerant()
        for node in input_circuit[self.NODES]:
            identifier = node[self.IDENTIFIER]
            if identifier in nodes:
                raise IdDuplicatedError("There are nodes duplicated.%i is duplicated", identifier)
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
                    next_component = self.get_component(next_component)
                    self._fill_id_mass_flow_inlet_nodes(id_mass_flow, prior_prior_id_mass_flow, next_component,
                                                        total_id_mass_flow)

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

    def get_refrigerant_library(self):
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


class ACircuitSerializer:
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

    def __init__(self):
        pass

    def deserialize(self, circuit_file):
        circuit = CircuitBuilder(circuit_file[self.IDENTIFIER])
        circuit.set_name(circuit_file[self.NAME])
        circuit.set_refrigerant(circuit_file[self.REFRIGERANT])
        circuit.set_refrigerant_library(circuit_file[self.REF_LIB])
        cmp_deserialize = cmp.AComponentSerializer()
        node_deserialize = nd.ANodeSerializer()
        for node in circuit_file[self.NODES]:
            new_node = node_deserialize.deserialize(node)
            circuit.add_node(new_node)
        for component in circuit_file[self.COMPONENTS]:
            new_cmp = cmp_deserialize.deserialize(component)
            circuit.add_component(new_cmp)

        return circuit

    def serialize(self, circuit):
        # Serializer object for node and component
        nd_serializer = nd.ANodeSerializer()
        cmp_serializer = cmp.AComponentSerializer()

        # Get circuit serialized
        circuit_serialized = {'name': circuit.get_name()}
        circuit_serialized['id'] = circuit.get_id()

        refrigerant = circuit.get_refrigerant()
        circuit_serialized['refrigerant'] = refrigerant.name()
        circuit_serialized['refrigerant_library'] = circuit.get_refrigerant_library()

        circuit_serialized['nodes'] = []
        nodes = circuit.get_nodes()
        for i in nodes:
            circuit_serialized['nodes'].append(nd_serializer.serialize(nodes[i]))

        circuit_serialized['components'] = []
        components = circuit.get_components()
        for i in components:
            circuit_serialized['components'].append(cmp_serializer.serialize(components[i]))

        return circuit_serialized


class CircuitBuilder:
    def __init__(self, id_):
        self._name = None
        self._id = id_
        self._id_count = Identifier()
        self._id_count.add_forbidden_id(id_)
        self._ref_lib = None
        self._refrigerant = None
        self._nodes = {}
        self._components = {}
        self._circuit = None

    def build(self):
        # Build the circuit object to solve.
        # Check if the input data is correct.
        if self._name is None:
            raise CircuitBuilderWarning('Circuit %s has no name', self._id)
        # Check if refrigerant library and refrigerant are initialized.
        if self._ref_lib is None:
            raise ValuePropertyError('Refrigerant library is not selected')
        if self._refrigerant is None:
            raise ValuePropertyError('Refrigerant is not selected')
        # Created circuit object
        self._circuit = Circuit(self._name, self._id, self._refrigerant.string, self._ref_lib.string)
        for node_id in self._nodes:
            node = self.get_node(node_id)
            try:
                self._circuit._add_node(node.build(self._circuit.get_refrigerant(), self._circuit.get_refrigerant_library()))
            except BuildError:
                raise BuildError
        for component_id in self._components:
            component = self.get_component(component_id)
            try:
                self._circuit._add_component(component.build())
            except BuildError:
                raise BuildError
        # Check if there are only one circuit (circuit is close because node are well defined).
        if not self._is_one_circuit():
            raise CircuitBuilderError('Circuit %s is not only one', self._id)

        self._circuit.configure()
        return self._circuit

    def _is_one_circuit(self):
        nodes_not_explored = list(self._nodes.keys())
        nodes_explored = [nodes_not_explored.pop()]
        nodes_to_explore = nodes_not_explored
        components_explored = []
        for node_id in nodes_to_explore:
            self._explore_circuit(components_explored, node_id, nodes_not_explored, nodes_to_explore)
        if len(nodes_not_explored) > 0:
            return False
        else:
            return True

    def _explore_circuit(self, components_explored, node_id, nodes_not_explored, nodes_to_explore):
        node = self.get_node(node_id)
        components_id = node.get_components_id()
        for component_id in components_id:
            if component_id not in components_explored:
                components_explored.append(component_id)
                component = self.get_component(component_id)
                outlet_nodes_id = component.get_outlet_nodes_id().copy()
                outlet_node_id = outlet_nodes_id.pop()
                nodes_to_explore += outlet_nodes_id
                try:
                    nodes_not_explored.remove(outlet_node_id)
                    self._explore_circuit(components_explored, outlet_node_id, nodes_not_explored, nodes_to_explore)
                except ValueError:
                    pass

    def set_name(self, name):
        self._name = StrRestricted(name)

    def set_refrigerant_library(self, ref_lib):
        self._ref_lib = StrRestricted(ref_lib, 'CoolPropHeos')

    def set_refrigerant(self, refrigent):
        self._refrigerant = StrRestricted(refrigent)

    def add_node(self, component_id_1, component_id_2):
        next_id = self._id_count.next
        new_node = nd.NodeBuilder(next_id, component_id_1, component_id_2)
        self._nodes[next_id] = new_node
        return new_node

    def add_node(self, node_builder_object):
        if isinstance(node_builder_object, nd.NodeBuilder):
            self._id_count.add_forbidden_id(node_builder_object.get_id())
            self._nodes[node_builder_object.get_id()] = node_builder_object

    def remove_node(self, rm_node):
        rm_node_id = rm_node.get_id()
        # Check the node is not use in nodes
        attached_components = rm_node.get_components_id()
        for component_id in attached_components:
            component = self.get_component(component_id)
            component.remove_node(rm_node_id)
        # Delete NodeBuilder object
        del self._components[rm_node_id]

    def get_node(self, node_id):
        return self._nodes[node_id]

    def add_component(self, component):
        if isinstance(component, cmp.ComponentBuilder):
            self._id_count.add_forbidden_id(component.get_id())
            self._components[component.get_id()] = component
        else:
            next_id = self._id_count.next
            new_component = cmp.ComponentBuilder(component, next_id)
            self._components[next_id] = new_component
            return new_component

    def remove_component(self, rm_component):
        rm_component_id = rm_component.get_id()
        # Check that the component is not use in nodes
        attached_nodes = rm_component.get_nodes_id()
        for node_id in attached_nodes:
            node = self.get_node(node_id)
            node.remove_component(rm_component_id)
        # Delete ComponentBuilder object
        del self._components[rm_component_id]

    def get_component(self, component_id):
        return self._components[component_id]
