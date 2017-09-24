# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Postsolver for circuit
"""


from scr.logic.solvers.postsolvers.postsolver import PostSolver


class Postsolver_v01(PostSolver):

    def post_solve(self, circuit):
        circuit = self._solve_nodes(circuit)
        circuit = self._solve_components(circuit)
        return circuit

    def _solve_nodes(self, circuit):
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

    def _solve_components(self, circuit):
        components = circuit.get_components()
        for component in components:
            component = components[component]
            self._solve_basic_properties(component)
            self._solve_auxiliary_properties(component)
        return circuit

    def _solve_basic_properties(self, cmp):
        self._solve_properties(cmp, cmp.get_basic_properties())

    def _solve_auxiliary_properties(self, cmp):
        self._solve_properties(cmp, cmp.get_auxiliary_properties())

    def _solve_properties(self, cmp, properties):
        for key in properties:
            cmp.solve_property(key)
