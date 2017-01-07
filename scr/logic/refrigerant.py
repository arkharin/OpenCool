# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Abstraction layer for CoolProp library
"""

import CoolProp as Cp


class Refrigerant:
    DENSITY = Cp.iDmass
    ENTROPY = Cp.iSmass
    QUALITY = Cp.iQ
    ENTHALPY = Cp.iHmass
    PRESSURE = Cp.iP
    TEMPERATURE = Cp.iT

    def __init__(self, backend, refrigerant):
        self._ref = Cp.AbstractState(backend, refrigerant)

    @staticmethod
    def build(backend, refrigerant):
        if backend is 'CoolPropHeos':
            return Refrigerant('HEOS', refrigerant)
        else:
            print('Error loading refrigerant library. %s is not found', backend)
            exit(1)

    def _update(self, property_type_1, property_1, property_type_2, property_2):
        input_keys = Cp.CoolProp.generate_update_pair(property_type_1, property_1, property_type_2, property_2)
        self._ref.update(input_keys[0], input_keys[1], input_keys[2])

    def T(self, property_type_1, property_1, property_type_2, property_2):
        self._update(property_type_1, property_1, property_type_2, property_2)
        return self._ref.T()

    def p(self, property_type_1, property_1, property_type_2, property_2):
        self._update(property_type_1, property_1, property_type_2, property_2)
        return self._ref.p()

    def h(self, property_type_1, property_1, property_type_2, property_2):
        self._update(property_type_1, property_1, property_type_2, property_2)
        return self._ref.hmass()

    def d(self, property_type_1, property_1, property_type_2, property_2):
        self._update(property_type_1, property_1, property_type_2, property_2)
        return self._ref.rhomass()

    def s(self, property_type_1, property_1, property_type_2, property_2):
        self._update(property_type_1, property_1, property_type_2, property_2)
        return self._ref.smass()

    def Q(self, property_type_1, property_1, property_type_2, property_2):
        self._update(property_type_1, property_1, property_type_2, property_2)
        return self._ref.Q()

    def T_crit(self):
        return self._ref.T_critical()

    def T_sat(self, pressure, Q=1.0):
        self._ref.update(Cp.PQ_INPUTS, pressure, Q)
        return self._ref.T()

    def p_sat(self, temperature, Q=1.0):
        self._ref.update(Cp.QT_INPUTS, Q, temperature)
        return self._ref.p()
