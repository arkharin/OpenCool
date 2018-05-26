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
from scr.logic.errors import PropertyValueError, BuildError, CircuitError, IdDuplicatedError, DeserializerError
from scr.logic.warnings import BuildWarning
import logging as log
from typing import Dict, List, Optional, Union


class Circuit:
    """Circuit class.

    Is the class used by the solver. It's constructed with the CircuitBuilder and assume that all arguments passed are
    correct.
    """
    def __init__(self, id_: int, refrigerant: str, refrigerant_library: str):
        self._id = id_
        self._ref_lib = refrigerant_library
        self._refrigerant = ref.Refrigerant.build(self.get_refrigerant_library(), refrigerant)
        self._nodes = {}
        self._components = {}
        self._mass_flows = []

    def _add_component(self, component_object: cmp.Component) -> None:
        """Add component object to circuit."""
        self._components[component_object.get_id()] = component_object

    def _add_node(self, node_object: nd.Node) -> None:
        """Add node object to circuit."""
        self._nodes[node_object.get_id()] = node_object

    def configure(self) -> None:
        """Configure circuit to solve it later."""
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
        """Search components that modify flows."""
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

    def _fill_nodes_with_mass_flow(self, id_mass_flow: int, node: nd.Node, stop_components: Dict[int, cmp.Component]) \
            -> None:
        """
        :raise: CircuitError.
        """
        # Count added to force while to finish.
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
                msg = f"Maximum iterations limit ({i}) reached in circuit  {self.get_id()} in " \
                       f"_fill_nodes_with_mass_flow method"
                log.error(msg)
                raise CircuitError(msg)
            else:
                node = inlet_component.get_outlet_node(inlet_component.get_id_outlet_nodes()[0])
            i += 1

    def get_component(self, id_component: int=None) -> cmp.Component:
        if id_component is None:
            id_component = self.get_components_id().pop()
        return self.get_components()[id_component]

    def get_components(self) -> Dict[int, cmp.Component]:
        return self._components

    def get_components_id(self) -> List[int]:
        return list(self._components.keys())

    def get_id(self) -> int:
        """Circuit id."""
        return self._id

    def get_mass_flows(self) -> List[float]:
        return self._mass_flows

    def get_node(self, id_node: Optional[int]=None) -> nd.Node:
        if id_node is None:
            id_node = self.get_nodes_id().pop()
        return self.get_nodes()[id_node]

    def get_nodes(self) -> Dict[int, nd.Node]:
        return self._nodes

    def get_nodes_id(self) -> List[int]:
        return list(self._nodes.keys())

    def get_refrigerant(self) -> ref.Refrigerant:
        return self._refrigerant

    def get_refrigerant_library(self) -> str:
        return self._ref_lib

    def get_components_by_type(self, component_type: str) -> Dict[int, cmp.Component]:
        """Return all components inside of the circuit that have the same type.

        :param component_type: One of component type defined in ComponentInfo class.
        """
        components = self.get_components()
        return {x: components[x] for x in components if
                components[x].get_component_info().get_component_type() == component_type}

    def update_mass_flows(self, mass_flows: List[float]) -> None:
        """Update mass flows with the floats in the list.

        :param mass_flows: mass flow of the circuit. List shall have the same length of the quantity of mass flow.
        :raise: CircuitError.
        """
        if len(mass_flows) != len(self.get_mass_flows()):
            msg = f"Try to updated mass {len(self.get_mass_flows())} with {len(mass_flows)} in circuit {self.get_id()}."
            log.error(msg)
            raise CircuitError(msg)
        i = 0
        for mass_flow in mass_flows:
            self.get_mass_flows()[i] = mass_flow
            i += 1


class ACircuitSerializer:
    """Serializer for the Circuit Class.

    Public attributes:
        - COMPONENTS
        - IDENTIFIER
        - NODES
        - REFRIGERANT
        - REF_LIB
    """
    COMPONENTS = 'components'
    IDENTIFIER = 'id'
    NODES = 'nodes'
    REFRIGERANT = 'refrigerant'
    REF_LIB = 'refrigerant_library'

    @staticmethod
    def deserialize(circuit_file: Dict) -> 'CircuitBuilder':
        """
        :raise DeserializerError
        """
        circuit = CircuitBuilder(circuit_file[ACircuitSerializer.IDENTIFIER])
        circuit.set_refrigerant(circuit_file[ACircuitSerializer.REFRIGERANT])
        circuit.set_refrigerant_library(circuit_file[ACircuitSerializer.REF_LIB])
        cmp_deserialize = cmp.AComponentSerializer()
        node_deserialize = nd.ANodeSerializer()
        try:
            for node in circuit_file[ACircuitSerializer.NODES]:
                new_node = node_deserialize.deserialize(node)
                circuit.create_node(new_node)
            for component in circuit_file[ACircuitSerializer.COMPONENTS]:
                new_cmp = cmp_deserialize.deserialize(component)
                circuit.create_component(new_cmp)

            return circuit
        except DeserializerError as e:
            raise e

    @staticmethod
    def serialize(circuit: Circuit) ->Dict:
        circuit_serialized = {ACircuitSerializer.IDENTIFIER: circuit.get_id()}
        refrigerant = circuit.get_refrigerant()
        circuit_serialized[ACircuitSerializer.REFRIGERANT] = refrigerant.name()
        circuit_serialized[ACircuitSerializer.REF_LIB] = circuit.get_refrigerant_library()

        circuit_serialized[ACircuitSerializer.NODES] = []
        # Serializer node object
        nd_serializer = nd.ANodeSerializer()
        nodes = circuit.get_nodes()
        for i in nodes:
            circuit_serialized[ACircuitSerializer.NODES].append(nd_serializer.serialize(nodes[i]))

        circuit_serialized[ACircuitSerializer.COMPONENTS] = []
        # Serializer component object
        cmp_serializer = cmp.AComponentSerializer()
        components = circuit.get_components()
        for i in components:
            circuit_serialized[ACircuitSerializer.COMPONENTS].append(cmp_serializer.serialize(components[i]))

        return circuit_serialized


class CircuitBuilder:
    """Builder class for circuit."""
    def __init__(self, id_: int) -> None:
        self._id = id_
        self._id_count = Identifier()
        self._id_count.add_used_id(id_)
        self._ref_lib = None
        self._refrigerant = None
        self._nodes = {}
        self._components = {}
        self._circuit = None

    def build(self) -> Circuit:
        """Build the circuit object to solve it later.

        Check if the input data is correct and build the circuit object sequentially.

        :raise BuildError: if fail to build correctly the circuit.
        """
        # Check if refrigerant library and refrigerant are initialized.
        if self._ref_lib is None:
            msg = "Refrigerant library is not selected"
            log.error(msg)
            raise BuildError(msg)
        if self._refrigerant is None:
            msg = "Refrigerant is not selected"
            log.error(msg)
            raise BuildError(msg)
        # Created circuit object
        self._circuit = Circuit(self._id, self._refrigerant.get(), self._ref_lib.get())
        for node_id in self._nodes:
            node = self.get_node(node_id)
            try:
                self._circuit._add_node(
                    node.build(self._circuit.get_refrigerant(), self._circuit.get_refrigerant_library()))
            except BuildError as e:
                raise e
        for component_id in self._components:
            component = self.get_component(component_id)
            try:
                self._circuit._add_component(component.build())
            except BuildError as e:
                raise e
        # Check if there are only one circuit (circuit is close because node are well defined).
        if not self.is_circuit_close():
            msg = f"Circuit {self.get_id()} is not close or there are more than one."
            log.error(msg)
            raise BuildError(msg)

        self._circuit.configure()
        return self._circuit

    def is_circuit_close(self):
        """Check if a circuit is close and unitary."""
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

    def _explore_node(self, n: int, cmp_explored: List[int], n_not_explored: List[int], n_to_explore: List[int]) \
            -> None:
        """
        Explore a node, move to next component with this inlet node, move to one of the outlet node of the component
        and save the other to explore they later.
        """
        cmps_attached = self.get_node(n).get_components()
        # Get an arbitrary component. Can't be used .pop() because node object it's affected to.
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

    def set_refrigerant_library(self, ref_lib: str) -> None:
        """
        :raise BuildWarning
        """
        try:
            self._ref_lib = StrRestricted(ref_lib, ['CoolPropHeos'])
        except PropertyValueError as e:
            log.warning(e)
            raise BuildWarning(e)
        # Only for NodeInfoFactory works with NodeBuilder object.
        for node_id in self.get_nodes():
            self.get_node(node_id)._set_refrigerant_library(ref_lib)

    def set_refrigerant(self, refrigerant: str) -> None:
        """
        :raise BuildWarning
        """
        try:
            self._refrigerant = StrRestricted(refrigerant)
        except PropertyValueError as e:
            log.warning(e)
            raise BuildWarning(e)
        # Only for NodeInfoFactory works with NodeBuilder object.
        for node_id in self.get_nodes():
            self.get_node(node_id)._set_refrigerant(refrigerant)

    def create_node(self, component_id_1: Optional[int] = None, component_id_2: Optional[int] = None) -> nd.NodeBuilder:
        """
         :raise BuildWarning
        """
        if component_id_1 is not None and component_id_1 not in self.get_components().keys():
            msg = f"Component 1 with ({component_id_1} isn't in the circuit {self.get_id()} and it isn't attached to " \
                  f"the node."
            log.warning(msg)
            raise BuildWarning(msg)

        if component_id_2 is not None and component_id_2 not in self.get_components().keys():
            msg = f"Component 2 with ({component_id_2} isn't in the circuit {self.get_id()} and it isn't attached to " \
                   f"the node."
            log.warning(msg)
            raise BuildWarning(msg)

        next_id = self._id_count.next
        # NodeBuilder can raise a BuildWarning.
        new_node = nd.NodeBuilder(next_id, component_id_1, component_id_2)
        self._nodes[next_id] = new_node
        refrigerant = self._refrigerant
        if refrigerant is not None:
            new_node._set_refrigerant(refrigerant)
        ref_lib = self._ref_lib
        if ref_lib is not None:
            new_node._set_refrigerant_library(ref_lib)
        return new_node

    def create_node(self, new_node: nd.NodeBuilder) -> nd.NodeBuilder:
        """
         :raise BuildWarning
        """
        if isinstance(new_node, nd.NodeBuilder):
            self._id_count.add_used_id(new_node.get_id())
            self._nodes[new_node.get_id()] = new_node
            refrigerant = self._refrigerant
            if refrigerant is not None:
                new_node._set_refrigerant(refrigerant)
            ref_lib = self._ref_lib
            if ref_lib is not None:
                new_node._set_refrigerant_library(ref_lib)
            return new_node
        else:
            msg = "New node can't be added, isn't a NodeBuilder"
            log.warning(msg)
            raise BuildWarning(msg)

    def remove_node(self, rm_node: nd.NodeBuilder) -> None:
        """
        :raise BuildWarning
        """
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
            msg = f"The node {rm_node_id} can't be deleted, isn't in the circuit."
            log.warning(msg)
            raise BuildWarning(msg)

    def get_node(self, node_id: int) -> nd.NodeBuilder:
        """
        :raise BuildWarning
        """
        try:
            return self._nodes[node_id]
        except KeyError:
            msg = f"Node {node_id} isn't in the circuit."
            log.warning(msg)
            raise BuildWarning(msg)

    def create_component(self, component_type: Union[str, cmp.ComponentBuilder]) -> cmp.ComponentBuilder:
        """
        :raise BuildWarning
        """
        if isinstance(component_type, cmp.ComponentBuilder):
            self._id_count.add_used_id(component_type.get_id())
            self._components[component_type.get_id()] = component_type
            return component_type
        else:
            next_id = self._id_count.next
            # ComponentBuilder can raise a BuildWarning.
            new_component = cmp.ComponentBuilder(next_id, component_type)
            self._components[next_id] = new_component
            return new_component

    def remove_component(self, rm_component: cmp.ComponentBuilder) -> None:
        """
        :raise BuildWarning
        """
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
            msg = f"The component {rm_component_id} can't be deleted, isn't in the circuit."
            log.warning(msg)
            raise BuildWarning(msg)

    def get_component(self, component_id: int) -> cmp.ComponentBuilder:
        """
        :raise BuildWarning
        """
        try:
            return self._components[component_id]
        except KeyError:
            msg = f"Node {component_id} isn't in the circuit."
            log.warning(msg)
            raise BuildWarning(msg)

    def get_components(self) -> Dict[int, cmp.ComponentBuilder]:
        return self._components

    def get_id(self) -> int:
        return self._id

    def get_nodes(self) -> Dict[int, nd.NodeBuilder]:
        return self._nodes


class Identifier:
    def __init__(self, forbidden_id: [List[int]]=list()):
        self._next_id = 0
        self._forbidden_id = forbidden_id

    @property
    def next(self):
        self._next_id = +1
        while self._next_id in self._forbidden_id:
            self._next_id = +1
        return self._next_id

    def add_used_id(self, id_):
        if id_ in self._forbidden_id:
            msg = f"The id {id_} is already in use."
            log.error(msg)
            raise IdDuplicatedError(msg)
        else:
            self._forbidden_id.append(id_)
