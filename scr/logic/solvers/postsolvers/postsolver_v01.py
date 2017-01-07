# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Postsolver for circuit
"""


from scr.logic.solvers.postsolvers.postsolver import PostSolver


class Postsolver_v01(PostSolver):

    def post_solve(self, circuit):
        components = circuit.get_components()
        for component in components:
            component = components[component]
            component.calculated_basic_properties()
            component.calculated_optional_properties()

        return circuit
