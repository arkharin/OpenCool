# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Postsolver for circuit
"""


from scr.logic.solvers.postsolvers.postsolver import PostSolver
from scr.logic.solvers.solver import SolutionResults as SR
from scr.logic.circuit import Circuit
from scr.logic.components.component import Component
from scr.logic.nodes.node import Node
from typing import Dict


class Postsolver_v01(PostSolver):

    def post_solve(self, circuit: Circuit) -> Dict:
        cir_id = circuit.get_id()
        circuit_solved = {SR.NODES: {}, SR.COMPONENTS: {}}
        for node in circuit.get_nodes():
            node_results = self._get_node_results(circuit.get_node(node))
            circuit_solved[SR.NODES][node] = node_results

        for component in circuit.get_components():
            component_results = self._get_component_results(circuit.get_component(component))
            circuit_solved[SR.COMPONENTS][component] = component_results

        return {cir_id: circuit_solved}

    def _get_node_results(self, node: Node) -> Dict:
        # Return dict with thermodynamic properties evaluated. Keys are global name of the properties.
        n_info = node.get_node_info()
        results = {}
        results[n_info.PRESSURE] = {SR.VALUE: node.pressure(), SR.UNIT: n_info.get_property(n_info.PRESSURE).get_unit()}
        results[n_info.TEMPERATURE] = {SR.VALUE: node.temperature(),
                                       SR.UNIT: n_info.get_property(n_info.TEMPERATURE).get_unit()}
        results[n_info.ENTHALPY] = {SR.VALUE: node.enthalpy(), SR.UNIT: n_info.get_property(n_info.ENTHALPY).get_unit()}
        results[n_info.DENSITY] = {SR.VALUE: node.density(), SR.UNIT: n_info.get_property(n_info.DENSITY).get_unit()}
        results[n_info.ENTROPY] = {SR.VALUE: node.entropy(), SR.UNIT: n_info.get_property(n_info.ENTROPY).get_unit()}
        results[n_info.QUALITY] = {SR.VALUE: node.quality(), SR.UNIT: n_info.get_property(n_info.QUALITY).get_unit()}
        results[n_info.MASS_FLOW] = {SR.VALUE: node.mass_flow(),
                                     SR.UNIT: n_info.get_property(n_info.MASS_FLOW).get_unit()}
        return results

    def _get_component_results(self, component: Component) -> Dict:
        basic_properties = self._serialize_properties(component, component.get_basic_properties())
        aux_properties = self._serialize_properties(component, component.get_auxiliary_properties())
        return {SR.BASIC_PROPERTIES: basic_properties, SR.AUXILIARY_PROPERTIES: aux_properties}

    def _serialize_properties(self, component: Component, properties: Dict) -> Dict:
        cmp_info = component.get_component_info()
        results = {}
        for i in properties:
            results[i] = {SR.VALUE: component.solve_property(i), SR.UNIT: cmp_info.get_property(i).get_unit()}
        return results

