# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Postsolver for circuit
"""


from scr.logic.solvers.postsolvers.postsolver import PostSolver


class Postsolver_v01(PostSolver):

    def post_solve(self, circuit):
        circuit = self._calculate_nodes_solved(circuit)
        circuit = self._calculated_components(circuit)
        return circuit

    def _calculate_nodes_solved(self, circuit):
        nodes = circuit.get_nodes()
        for node in nodes:
            node = nodes[node]
            # Update node values with last base value calculated.
            node.update_node_values(node.get_type_property_base_1(), node.get_value_property_base_1(),
                                    node.get_type_property_base_2(), node.get_value_property_base_2())
            # Calculate all thermodynamic properties.
            node.pressure()
            node.temperature()
            node.enthalpy()
            node.density()
            node.entropy()
            node.quality()

        return circuit

    def _calculated_components(self, circuit):
        components = circuit.get_components()
        for component in components:
            component = components[component]
            self._calculated_basic_properties(component)
            self._calculated_optional_properties(component)
        return circuit

    def _calculated_basic_properties(self, cmp):
        self._calculate_properties(cmp, cmp.get_basic_properties())

    def _calculated_optional_properties(self, cmp):
        self._calculate_properties(cmp, cmp.get_optional_properties())

    def _calculate_properties(self, cmp, properties):
        for key in properties:
            cmp.solve_property(key)
