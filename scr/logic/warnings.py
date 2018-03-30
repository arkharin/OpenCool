# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define warnings find in the program
"""


class ComponentBuilderWarning(RuntimeWarning):
    pass


class NodeBuilderWarning(RuntimeWarning):
    pass


class CircuitBuilderWarning(RuntimeWarning):
    pass


class ComponentWarning(RuntimeWarning):
    pass


class InitialValuesWarning(RuntimeWarning):
    pass


class PreSolverWarning(RuntimeWarning):
    pass
