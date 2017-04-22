# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Presolver for simple circuit
"""


from scr.logic.solvers.presolvers.presolver import PreSolver
import scr.logic.nodes.node as nd
from scr.logic.components.component import Component
import scr.logic.components.condenser.theoretical as Condenser
import scr.logic.components.evaporator.theoretical as Evaporator
from scr.logic.errors import TypeComponentError

COMPRESSOR = Component.COMPRESSOR
CONDENSER = Component.CONDENSER
EVAPORATOR = Component.EVAPORATOR
EXPANSION_VALVE = Component.EXPANSION_VALVE


class Presolver_v01 (PreSolver):
    FORWARD = 'FORWARD'
    BACKWARD = 'BACKWARD'

    def calculate_initial_conditions(self, circuit):
        condensers = circuit.search_components_by_type(CONDENSER)
        evaporators = circuit.search_components_by_type(EVAPORATOR)
        expansion_valves = circuit.search_components_by_type(EXPANSION_VALVE)
        # TODO ahora es un dict. revisar q varia.
        from_components = condensers.copy()
        from_components.update(expansion_valves)
        from_components.update(evaporators)
        stop_components = [COMPRESSOR, CONDENSER, EVAPORATOR, EXPANSION_VALVE]
        mass_flow, pc, pe, tc, te, tsc, tsh = self._initial_values(circuit, condensers, evaporators)
        self._fill_nodes(from_components, pc, pe, stop_components, tc, te, tsc, tsh)
        mass_flows = self._fill_mass_flows(circuit, mass_flow)
        initial_conditions = self._fill_initial_conditions(circuit, mass_flows)
        return initial_conditions

    def _fill_initial_conditions(self, circuit, mass_flows):
        initial_conditions = []
        nodes = circuit.get_nodes()
        for node in nodes:
            node = nodes[node]
            initial_conditions.append(node.get_value_property_base_1())
            initial_conditions.append(node.get_value_property_base_2())
        for m_flow in mass_flows:
            initial_conditions.append(m_flow)
        return initial_conditions

    def _fill_mass_flows(self, circuit, mass_flow):
        mass_flows = circuit.get_mass_flows()
        mass_flow = [mass_flow] * len(mass_flows)
        circuit.update_mass_flows(mass_flow)
        return mass_flows

    def _fill_nodes(self, from_components, pc, pe, stop_components, tc, te, tsc, tsh):
        for i in from_components:
            component = from_components[i]
            if component.get_type() == CONDENSER:
                node_property_type_1 = nd.Node.PRESSURE
                property_1 = pc
                # TODO Values are hardcoded
                node_property_type_2 = nd.Node.TEMPERATURE
                property_2 = tc + 30
                fill_direction = self.BACKWARD
                nodes = component.get_inlet_nodes()

            elif component.get_type() == EVAPORATOR:
                node_property_type_1 = nd.Node.PRESSURE
                property_1 = pe
                node_property_type_2 = nd.Node.TEMPERATURE
                property_2 = te + tsh
                fill_direction = self.FORWARD
                nodes = component.get_outlet_nodes()

            elif component.get_type() == EXPANSION_VALVE:
                node_property_type_1 = nd.Node.PRESSURE
                property_1 = pc
                node_property_type_2 = nd.Node.TEMPERATURE
                property_2 = tc - tsc
                fill_direction = self.BACKWARD
                nodes = component.get_inlet_nodes()
                self._fill_nodes_from_component_to_component(component, fill_direction, stop_components, node_property_type_1, property_1,
                                                        node_property_type_2, property_2)
                property_1 = pe
                node_property_type_2 = nd.Node.QUALITY
                property_2 = 0.3
                fill_direction = self.FORWARD
                nodes = component.get_outlet_nodes()
            else:
                raise TypeComponentError("Solver don't recognize component type")
            self._fill_nodes_from_component_to_component(component, fill_direction, stop_components,
                                                         node_property_type_1, property_1, node_property_type_2,
                                                         property_2)

    def _initial_values(self, circuit, condensers, evaporators):
        # TODO Values are hardcoded
        refrigerant = circuit.get_refrigerant()
        for evaporator in evaporators:
#            te = evaporators[evaporator].get_basic_property(Evaporator.Theoretical.SATURATION_TEMPERATURE)
            te = 263.15
        pe = refrigerant.p(refrigerant.TEMPERATURE, te, refrigerant.QUALITY, 1.0)
        tsh = 5.0
        for condenser in condensers:
            tc = condensers[condenser].get_basic_property(Condenser.Theoretical.SATURATION_TEMPERATURE)
        pc = refrigerant.p(refrigerant.TEMPERATURE, tc, refrigerant.QUALITY, 1.0)
        tsc = 2.0
        mass_flow = 0.20
        return mass_flow, pc, pe, tc, te, tsc, tsh

    def _fill_nodes_from_component_to_component(self, component, fill_direction, stop_components, property_node_type_1,
                                                property_1, property_node_type_2, property_2):
        if fill_direction == self.FORWARD:
            nodes = component.get_outlet_nodes()
        else:
            nodes = component.get_inlet_nodes()
        for i in nodes:
            node = nodes[i]
            if not node.is_init():
                node.update_node_values(property_node_type_1, property_1, property_node_type_2, property_2)
                next_components = node.get_components_attached()
                for next_component in next_components:
                    next_component = next_components[next_component]
                    if next_component.get_type() not in stop_components:
                        self._fill_nodes_from_component_to_component(next_component, fill_direction, stop_components, property_node_type_1,
                                                                property_1, property_node_type_2, property_2)