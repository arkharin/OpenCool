# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define the abstract class PostSolver.
"""

from abc import ABC, abstractmethod
from importlib import import_module


class PostSolver (ABC):
    def __init__(self):
        pass

    @staticmethod
    def build(postsolver_name):
        # Dynamic importing modules
        try:
            cmp = import_module('scr.logic.solvers.postsolvers.' + postsolver_name)
        except ImportError:
            print('Error loading postsolver. Type: %s is not found', postsolver_name)
            exit(1)
        # Only capitalize the first letter
        class_name = postsolver_name.replace(postsolver_name[0], postsolver_name[0].upper(), 1)
        class_ = getattr(cmp, class_name)
        return class_()

    @abstractmethod
    def post_solve(self, circuit):
        pass
