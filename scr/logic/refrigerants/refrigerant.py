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

    # If is not specify, all units in SI.
    def __init__(self, backend, refrigerant):
        self._ref = Cp.AbstractState(backend, refrigerant)

    @staticmethod
    def build(backend, refrigerant):
        if backend == 'CoolPropHeos':
            return Refrigerant('HEOS', refrigerant)
        else:
            print('Error loading refrigerant library. %s is not found', backend)
            exit(1)

    def _update(self, property_type_1, property_1, property_type_2, property_2):
        input_keys = Cp.CoolProp.generate_update_pair(property_type_1, property_1, property_type_2, property_2)
        self._ref.update(input_keys[0], input_keys[1], input_keys[2])

    def T(self, property_type_1, property_1, property_type_2, property_2):
        # Return temperature in Kelvin.
        self._update(property_type_1, property_1, property_type_2, property_2)
        return self._ref.T()

    def p(self, property_type_1, property_1, property_type_2, property_2):
        # Return absolute pressure un Pascals.
        self._update(property_type_1, property_1, property_type_2, property_2)
        return self._ref.p()

    def h(self, property_type_1, property_1, property_type_2, property_2):
        # Return enthalpy in J/kg.
        self._update(property_type_1, property_1, property_type_2, property_2)
        return self._ref.hmass()

    def d(self, property_type_1, property_1, property_type_2, property_2):
        # Return density in kg/m3.
        self._update(property_type_1, property_1, property_type_2, property_2)
        return self._ref.rhomass()

    def s(self, property_type_1, property_1, property_type_2, property_2):
        # Return entropy in J/kg·K.
        self._update(property_type_1, property_1, property_type_2, property_2)
        return self._ref.smass()

    def Q(self, property_type_1, property_1, property_type_2, property_2):
        # Return vapor quality; 0 = saturated liquid, 1 = saturated vapour, <0 if one phase.
        self._update(property_type_1, property_1, property_type_2, property_2)
        return self._ref.Q()

    def T_crit(self):
        # Return critical temperature in Kelvin.
        return self._ref.T_critical()

    def p_crit(self):
        # Return critical temperature in Kelvin.
        return self._ref.p_critical()

    def T_sat(self, pressure, Q=1.0):
        # Return saturated temperature in Kelvin.
        self._ref.update(Cp.PQ_INPUTS, pressure, Q)
        return self._ref.T()

    def p_sat(self, temperature, Q=1.0):
        # Return critical pressure in Pascals.
        self._ref.update(Cp.QT_INPUTS, Q, temperature)
        return self._ref.p()

    def name(self):
        # Return a string.
        return self._ref.name()

    # Refrigerant property limits. If there are no limit, return None.
    # TODO Coolprop 6.1.0 doesn't support check all limits. All not supported, are harcorded
    def Tmin(self):
        return self._ref.Tmin()

    def Tmax(self):
        return self._ref.Tmax()

    def pmin(self):
        return 0.0

    def pmax(self):
        return self._ref.pmax()

    def dmin(self):
        return 0.0

    def dmax(self):
        return None

    def hmin(self):
        return 0.0

    def hmax(self):
        return None

    def smin(self):
        return 0.0

    def smax(self):
        return None

    def Qmin(self):
        return 0.0

    def Qmax(self):
        return 1.0
