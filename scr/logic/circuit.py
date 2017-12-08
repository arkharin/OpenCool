# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the circuit class
"""

import scr.logic.components.component as cmp
import scr.logic.nodes.node as nd
import scr.logic.refrigerants.refrigerant as ref
from scr.helpers.properties import StrRestricted
from scr.logic.errors import ValuePropertyError, CircuitBuilderError, BuildError, CalculationError, IdDuplicatedError
from scr.logic.warnings import CircuitBuilderWarning


class Circuit:
    def __init__(self, id_, refrigerant, refrigerant_library):
        self._id = id_
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
        self._init_mass_flows()
        for node_id in self.get_nodes():
            node = self.get_node(node_id)
            # A list of all mass_flows of te circuit is passes to node. Later, will be configurated which mass flow it
            # is the correct.
            node.configure(self.get_components(), self.get_mass_flows())

        for component_id in self.get_components():
            component = self.get_component(component_id)
            component.configure(self.get_nodes())

        self._link_nodes_mass_flows()

    def _init_mass_flows(self):
        separate_components = self.get_components_by_type(cmp.ComponentInfo.SEPARATOR_FLOW)
        self._mass_flows = [0.0] * (2 * len(separate_components) + 1)

    def _link_nodes_mass_flows(self):
        # Search components that modify flows
        mix_components = self.get_components_by_type(cmp.ComponentInfo.MIXER_FLOW)
        separate_components = self.get_components_by_type(cmp.ComponentInfo.SEPARATOR_FLOW)
        flow_components = {**separate_components, **mix_components}
        # Create and fill id_mass_flow in nodes.
        # If it is a simple circuit, it is easier link all nodes mass flows
        if len(flow_components) == 0:
            id_mass_flow = 0
            id_component = self.get_components_id()[0]
            component = self.get_component(id_component)
            id_node = component.get_id_outlet_nodes()[0]
            outlet_node = component.get_outlet_node(id_node)
            self._fill_nodes_with_mass_flow(id_mass_flow, outlet_node, {id_component: component})
        else:
            id_mass_flow = 0
            for id_component in mix_components:
                component = self.get_component(id_component)
                # A mix component only have one outlet
                id_outlet_node = component.get_id_outlet_nodes()[0]
                outlet_node = component.get_outlet_node(id_outlet_node)
                self._fill_nodes_with_mass_flow(id_mass_flow, outlet_node, flow_components)
                id_mass_flow += 1

            for id_component in separate_components:
                component = self.get_component(id_component)
                outlet_nodes = component.get_outlet_nodes()
                for id_node in outlet_nodes:
                    node = component.get_outlet_node(id_node)
                    self._fill_nodes_with_mass_flow(id_mass_flow, node, flow_components)
                    id_mass_flow += 1

    def _fill_nodes_with_mass_flow(self, id_mass_flow, node, stop_components):
        # Count added to force while to finish
        i = 0
        while True:
            node.set_id_mass_flow(id_mass_flow)
            # This components only have one outlet because is not a flow component.
            inlet_component = node.get_inlet_component_attached()
            id_inlet_component = inlet_component.get_id()
            if id_inlet_component in stop_components:
                break
            # Only to force to finish the while
            elif i > 1000:
                raise CalculationError('Maximum iterations limit reached in circuit ' + self.get_id() +
                                       ' in _fill_nodes_with_mass_flow method')
            else:
                node = inlet_component.get_outlet_node(inlet_component.get_id_outlet_nodes()[0])
            i += 1

    def get_component(self, id_component):
        return self.get_components()[id_component]

    def get_components(self):
        return self._components

    def get_components_id(self):
        return list(self._components.keys())

    def get_id(self):
        return self._id

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

    def get_components_by_type(self, component_type):
        components = self.get_components()
        return {x: components[x] for x in components if
                components[x].get_component_info().get_component_type() == component_type}

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
    NODES = 'nodes'
    OPTIONAL_PROPERTIES = 'optional properties'
    OUTLET_NODES = 'outlet nodes'
    REFRIGERANT = 'refrigerant'
    REF_LIB = 'refrigerant_library'

    def __init__(self):
        pass

    def deserialize(self, circuit_file):
        circuit = CircuitBuilder(circuit_file[self.IDENTIFIER])
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
        # Get circuit serialized
        circuit_serialized = {'id': circuit.get_id()}
        refrigerant = circuit.get_refrigerant()
        circuit_serialized['refrigerant'] = refrigerant.name()
        circuit_serialized['refrigerant_library'] = circuit.get_refrigerant_library()

        circuit_serialized['nodes'] = []
        # Serializer node object
        nd_serializer = nd.ANodeSerializer()
        nodes = circuit.get_nodes()
        for i in nodes:
            circuit_serialized['nodes'].append(nd_serializer.serialize(nodes[i]))

        circuit_serialized['components'] = []
        # Serializer component object
        cmp_serializer = cmp.AComponentSerializer()
        components = circuit.get_components()
        for i in components:
            circuit_serialized['components'].append(cmp_serializer.serialize(components[i]))

        return circuit_serialized


class CircuitBuilder:
    def __init__(self, id_):
        self._id = id_
        self._id_count = Identifier()
        self._id_count.add_used_id(id_)
        self._ref_lib = None
        self._refrigerant = None
        self._nodes = {}
        self._components = {}
        self._circuit = None

    def build(self):
        # Build the circuit object to solve.
        # Check if the input data is correct.
        # Check if refrigerant library and refrigerant are initialized.
        if self._ref_lib is None:
            raise ValuePropertyError('Refrigerant library is not selected')
        if self._refrigerant is None:
            raise ValuePropertyError('Refrigerant is not selected')
        # Created circuit object
        self._circuit = Circuit(self._id, self._refrigerant.get(), self._ref_lib.get())
        for node_id in self._nodes:
            node = self.get_node(node_id)
            try:
                self._circuit._add_node(
                    node.build(self._circuit.get_refrigerant(), self._circuit.get_refrigerant_library()))
            except BuildError:
                raise BuildError
        for component_id in self._components:
            component = self.get_component(component_id)
            try:
                self._circuit._add_component(component.build())
            except BuildError:
                raise BuildError
        # Check if there are only one circuit (circuit is close because node are well defined).
        if not self.is_circuit_close():
            raise CircuitBuilderError('Circuit ' + str(self.get_id()) + ' is not close or there are more than one')

        self._circuit.configure()
        return self._circuit

    def is_circuit_close(self):
        # List of nodes not explored
        n_not_explored = list(self.get_nodes().keys())
        # We want one aleatory component id.
        c_id = list(self.get_components().keys())
        c_id = c_id[0]
        # Save the components id already explored.
        cmp_explored = [c_id]
        # List for remember nodes to explore when there are more than one outlet node in a component.
        n_to_explore = self.get_component(c_id).get_outlet_nodes().copy()
        for n in n_to_explore:
            n_not_explored.remove(n)
            # Explore the node and advance to the next node to explore.
            self._explore_node(n, cmp_explored, n_not_explored, n_to_explore)

        if len(n_not_explored) > 0:
            return False
        else:
            return True

    def _explore_node(self, n, cmp_explored, n_not_explored, n_to_explore):
        # Explore a node, move to next component with this inlet node, move to one of the outlet node of the component
        # and save the other to explore they later.
        cmps_attached = self.get_node(n).get_components()
        # Get an arbritary component. Can't be used .pop() because node object it's affected to.
        c = cmps_attached[0]
        if c in cmp_explored:
            c = cmps_attached[1]
        if c not in cmp_explored:
            cmp_explored.append(c)
            n_outs = self.get_component(c).get_outlet_nodes().copy()
            n_out = n_outs.pop()
            n_not_explored.remove(n_out)
            n_to_explore += n_outs
            self._explore_node(n_out, cmp_explored, n_not_explored, n_to_explore)

    def set_refrigerant_library(self, ref_lib):
        self._ref_lib = StrRestricted(ref_lib, 'CoolPropHeos')

    def set_refrigerant(self, refrigent):
        self._refrigerant = StrRestricted(refrigent)

    def add_node(self, component_id_1, component_id_2):
        if component_id_1 in self.get_components().keys() and component_id_2 in self.get_components().keys():
            next_id = self._id_count.next
            new_node = nd.NodeBuilder(next_id, component_id_1, component_id_2)
            self._nodes[next_id] = new_node
            return new_node
        else:
            raise CircuitBuilderWarning('New node can\'t be added. One component is not in the circuit')

    def add_node(self, node_builder_object):
        if isinstance(node_builder_object, nd.NodeBuilder):
            self._id_count.add_used_id(node_builder_object.get_id())
            self._nodes[node_builder_object.get_id()] = node_builder_object
        else:
            raise CircuitBuilderWarning('New node can\'t be added. Object is not a node')

    def remove_node(self, rm_node):
        rm_node_id = rm_node.get_id()
        if rm_node_id in self.get_nodes().keys():
            # Check the node is not use in components
            attached_components = rm_node.get_components()
            for component_id in attached_components:
                component = self.get_component(component_id)
                component.remove_node(rm_node_id)
            # Delete NodeBuilder object
            del self._components[rm_node_id]
        else:
            raise CircuitBuilderWarning('The node ' + str(rm_node_id) + ' can\'t be deleted. Is not in the circuit')

    def get_node(self, node_id):
        return self._nodes[node_id]

    def add_component(self, component):
        if isinstance(component, cmp.ComponentBuilder):
            self._id_count.add_used_id(component.get_id())
            self._components[component.get_id()] = component
        else:
            next_id = self._id_count.next
            new_component = cmp.ComponentBuilder(component, next_id)
            self._components[next_id] = new_component
            return new_component

    def remove_component(self, rm_component):
        rm_component_id = rm_component.get_id()
        if rm_component_id in self.get_components().keys():
            # Check that the component is not use in nodes
            attached_nodes = rm_component.get_attached_nodes()
            for node_id in attached_nodes:
                node = self.get_node(node_id)
                node.remove_component(rm_component_id)
            # Delete ComponentBuilder object
            del self._components[rm_component_id]
        else:
            raise CircuitBuilderWarning(
                'The component ' + str(rm_component_id) + ' can\'t be deleted. Is not in the circuit')

    def get_component(self, component_id):
        return self._components[component_id]

    def get_components(self):
        return self._components

    def get_id(self):
        return self._id

    def get_nodes(self):
        return self._nodes


class Identifier:
    def __init__(self, *forbidden_id):
        self._next_id = 0
        self._forbidden_id = list(forbidden_id)

    @property
    def next(self):
        self._next_id = +1
        while self._next_id in self._forbidden_id:
            self._next_id = +1
        return self._next_id

    def add_used_id(self, id_):
        if id_ in self._forbidden_id:
            raise IdDuplicatedError('This id %s is already in use', id_)
        else:
            self._forbidden_id.append(id_)
