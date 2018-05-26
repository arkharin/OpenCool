# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Define initial values usage in the presolver.

Define InitialValues class.
"""

from scr.logic.warnings import InitialValuesWarning
from scr.logic.errors import InitialValuesError
from scr.helpers.properties import NumericProperty as NP
from scr.logic.nodes.node import NodeInfoFactory, Node, NodeBuilder
from scr.logic.nodes.node import NodeInfo as NdInfo
from math import inf
from scr.logic.circuit import ACircuitSerializer, Circuit
from typing import TypeVar, Tuple, Optional


class InitialValues:
    """
    Initial values inside a circuit.

    Initial values are in the nodes scope. It isn't possible assign a initial value directly to a component. Supported
    initial properties:
        - Pressure
        - Temperature
        - Enthalpy
        - Density
        - Entropy
        - Quality
        - Mass flow
        - Saturation temperature
        - Thermal power  (Can be a cooling power or heating power and always positive).

    Attributes
        - P --  pressure.
        - T -- temperature.
        - H -- enthalpy
        - D -- density
        - S -- entropy
        - Q -- vapour quality
        - M -- mass flow
        - TSAT -- saturation temperature
        - Qpower -- thermal power. Can be a cooling power or heating power. Always positive.
        - X0_DATA -- initial values
    """
    # Properties allowed.
    # Properties not dependant of other nodes
    P = 'Pressure'
    T = 'Temperature'
    H = 'Enthalpy'
    D = 'Density'
    S = 'Entropy'
    Q = 'Quality'
    M = 'Mass flow'
    TSAT = 'Saturation temperature'
    # Properties not supported because I don't know how to manage them in the ComplexPresolver:
    # TSH = 'Superheating'
    # TSC = 'Subcooling'

    # Properties dependant of other nodes
    Qpower = 'Thermal power'  # Can be a cooling power or heating power. Always positive.
    # Properties not supported because I don't know how to manage them in the ComplexPresolver:
    # DP = 'Pressure drop'
    # TDP = 'Temperature pressure drop'
    # DT = 'Temperature differential'

    # Name initial values data entry in file
    X0_DATA = "initial values"

    Ref = TypeVar('Ref', str, Node, NodeBuilder)

    def __init__(self, refrigerant: Ref, ref_library: str ='CoolPropHeos') -> None:
        """

        :param refrigerant: refrigerant.
        :param ref_library: Refrigerant library to use.
        """
        self._nd = {}  # Node initial values.

        # Define initial values properties.
        ni = NodeInfoFactory.get(refrigerant, ref_library)
        # Properties to assign directly to a node.
        prop = ni.get_property(ni.PRESSURE)
        lim = prop.get_limits()
        un = prop.get_unit()
        self._props = {self.P: [NP(lower_boundary=lim[0], upper_boundary=lim[1], unit=un), NdInfo.PRESSURE,
                                self._calculate_x0_P, 0]}
        prop = ni.get_property(ni.TEMPERATURE)
        lim = prop.get_limits()
        un = prop.get_unit()
        self._props[self.T] = [NP(lower_boundary=lim[0], upper_boundary=lim[1], unit=un), NdInfo.TEMPERATURE,
                               self._calculate_x0_T, 0]
        prop = ni.get_property(ni.ENTHALPY)
        lim = prop.get_limits()
        un = prop.get_unit()
        self._props[self.H] = [NP(lower_boundary=lim[0], upper_boundary=lim[1], unit=un), NdInfo.ENTHALPY,
                               self._calculate_x0_H, 0]
        prop = ni.get_property(ni.ENTROPY)
        lim = prop.get_limits()
        un = prop.get_unit()
        self._props[self.S] = [NP(lower_boundary=lim[0], upper_boundary=lim[1], unit=un), NdInfo.ENTROPY,
                               self._calculate_x0_S, 0]
        prop = ni.get_property(ni.DENSITY)
        lim = prop.get_limits()
        un = prop.get_unit()
        self._props[self.D] = [NP(lower_boundary=lim[0], upper_boundary=lim[1], unit=un), NdInfo.DENSITY,
                               self._calculate_x0_D]
        prop = ni.get_property(ni.QUALITY)
        lim = prop.get_limits()
        un = prop.get_unit()
        self._props[self.Q] = [NP(lower_boundary=lim[0], upper_boundary=lim[1], unit=un), NdInfo.QUALITY,
                               self._calculate_x0_Q, 0]
        prop = ni.get_property(ni.MASS_FLOW)
        lim = prop.get_limits()
        un = prop.get_unit()
        self._props[self.M] = [NP(lower_boundary=lim[0], upper_boundary=lim[1], unit=un), NdInfo.MASS_FLOW,
                               self._calculate_x0_M, 0]
        # Basic properties not found in a node.
        prop = ni.get_property(ni.TEMPERATURE)
        un = prop.get_unit()
        self._props[self.TSAT] = [NP(lower_boundary=0, upper_boundary=inf, unit=un), NdInfo.PRESSURE,
                                  self._calculate_x0_TSAT, 0]
        # Properties not supported because I don't know how to manage them in the ComplexPresolver:
        # self._props[self.TSH] = [NP(lower_boundary=0, upper_boundary=inf, unit=un), NdInfo.TEMPERATURE,
        #                          self._calculate_x0_TSH, 0]
        # self._props[self.TSC] = [NP(lower_boundary=0, upper_boundary=inf, unit=un), NdInfo.TEMPERATURE,
        #                          self._calculate_x0_TSC, 0]

        # More advanced properties.
        self._props[self.Qpower] = [NP(lower_boundary=0, upper_boundary=inf, unit='kW'), NdInfo.MASS_FLOW,
                                    self._calculate_x0_Qpower, 1]
        # prop = ni.get_property(ni.PRESSURE)
        # un = prop.get_unit()
        # Properties not supported because I don't know how to manage them in the ComplexPresolver:
        # self._props[self.DP] = [NP(lower_boundary=0, upper_boundary=inf, unit=un), NdInfo.PRESSURE,
        #                         self._calculate_x0_DP, 1]
        # prop = ni.get_property(ni.TEMPERATURE)
        # un = prop.get_unit()
        # self._props[self.TDP] = [NP(lower_boundary=0, upper_boundary=inf, unit=un), NdInfo.PRESSURE,
        #                          self._calculate_x0_TDP, 1]
        # self._props[self.DT] = [NP(lower_boundary=0, upper_boundary=inf, unit=un), NdInfo.TEMPERATURE,
        #                         self._calculate_x0_DT, 1]

    def add(self, node_id: int, prop: str, value: float, *args: Tuple[int]) -> None:
        """
        Add an initial value to a node.

        An initial value is added to a property of a node. The property can depend of the other node values.

        :param node_id: node identifier to add the property
        :param prop: The property to use value. The allowed properties are: 'Pressure', 'Temperature', 'Enthalpy',
         'Density', 'Entropy', 'Quality', 'Mass flow', 'Saturation temperature', 'Thermal power'.
         Not suported properties because I don't know how to manage them in the ComplexPresolver: 'Superheating',
         'Subcooling','Pressure drop', 'Temperature pressure drop', 'Temperature differential'.
        :param value: property value
        :param args: Nodes to use for calculated the advance property.
        :raise: InitialValuesError if property bad defined.
        :raise: InitialValuesWarning if can be used the property as initial property

        For example: add(1, 'T', 293.15): add to node 1, a temperature of 293.15
        example 2: add(2, 'Thermal power', 1000, 1)

        """
        if prop in self._props:
            prop_info = self.get_property_info(prop)
            if prop_info[0].is_correct(value):
                if node_id not in self._nd:
                    self._nd[node_id] = {prop: []}
                if prop in self.get_mass_flow_properties() and len(self._nd[node_id]) > 3:
                    raise InitialValuesError(f"The node {node_id} only can have two initial properties")
                elif len(self._nd[node_id]) > 2:
                    raise InitialValuesError(f"The node {node_id} only can have two initial properties")
                self._nd[node_id][prop] = [value]
                for arg in args:
                    self._nd[node_id][prop].append(arg)
                if len(self._nd[node_id][prop]) != (prop_info[3] + 1):
                    raise InitialValuesError(f"PropertyName {prop} is not correctly defined")
            else:
                raise InitialValuesError(f"{value} must be between {self.get_property_info(prop)[0].get_limits()} for"
                                         f" property {prop}")
        else:
            raise InitialValuesWarning(f"PropertyName {prop} can't be used as initial value")

    def remove(self, node_id: int, *args: Tuple[str]) -> None:
        """Remove the initial values of the node.

        By default all properties are removed. If properties are specified, removed only that.
        :raise InitialValuesWarning if property/properties doesn't exist
        """
        if len(args) > 0:
            for prop in args:
                try:
                    self._nd[node_id].pop(prop)
                except KeyError:
                    raise InitialValuesWarning(f"The property {prop} doesn't exist in the node: {node_id}")
        else:
            try:
                self._nd.pop(node_id)
            except KeyError:
                raise InitialValuesWarning(f"The node {node_id} doesn't have any initial value")

    def get(self, node_id: int) -> Optional[dict]:
        """Initial values of a node"""
        if node_id in self._nd:
            return self._nd[node_id]
        else:
            return None

    def get_property(self, node_id: int, prop: str) -> Optional[list]:
        """:return: [value, node id j related, node k,..."""
        n = self.get(node_id)
        if n is None:
            return None
        else:
            try:
                return n[prop]
            except KeyError:
                return None

    def get_allowed_properties(self) -> list:
        """Return allowed properties to use for initial values of the nodes"""
        return list(self._props.keys())

    def get_basic_properties(self) -> list:
        """Return thermodynamic properties of a node that are not dependent of other thermodynamic properties"""
        return [self.P, self.T, self.H, self.D, self.S, self.Q, self.TSAT]

    def get_mass_flow_properties(self) -> list:
        """Properties related to mass flow"""
        return [self.M, self.Qpower]

    def get_nodes_id(self) -> list:
        return list(self._nd.keys())

    def get_property_info(self, prop_name: str) -> list:
        """PropertyName information

        :return: [NumericProperty, (NodeInfo property) Node property equivalent, (callable) function for calculated
                        the property, number of extra nodes required]
        :raise: InitialValuesError if prop_name is not a PropertyName
        """
        if prop_name in self._props:
            return self._props[prop_name]
        else:
            raise InitialValuesError(f"PropertyName {prop_name} not allowed for initial value")

    # PropertyName equations:
    # Function API: func(node id, circuit object)
    def _calculate_x0_P(self, nd_id: int, circuit: Circuit) -> float:
        return self.get_property(nd_id, self.P)[0]

    def _calculate_x0_T(self, nd_id: int, circuit: Circuit) -> float:
        return self.get_property(nd_id, self.T)[0]

    def _calculate_x0_H(self, nd_id: int, circuit: Circuit) -> float:
        return self.get_property(nd_id, self.H)[0]

    def _calculate_x0_D(self, nd_id: int, circuit: Circuit) -> float:
        return self.get_property(nd_id, self.D)[0]

    def _calculate_x0_S(self, nd_id: int, circuit: Circuit) -> float:
        return self.get_property(nd_id, self.S)[0]

    def _calculate_x0_Q(self, nd_id: int, circuit: Circuit) -> float:
        return self.get_property(nd_id, self.Q)[0]

    def _calculate_x0_M(self, nd_id: int, circuit: Circuit) -> float:
        return self.get_property(nd_id, self.M)[0]

    def _calculate_x0_TSAT(self, nd_id: int, circuit: Circuit) -> float:
        tsat = self.get_property(nd_id, self.TSAT)[0]
        n = circuit.get_node(nd_id)
        return n.get_refrigerant().p_sat(tsat)

    # Properties not supported because I don't know how to manage them in the ComplexPresolver:
    # def _calculate_x0_TSH(self, nd_id: int, circuit: Circuit) -> float:
    #     tsh = self.get_property(nd_id, self.TSH)[0]
    #     n = circuit.get_node(nd_id)
    #     p = n.pressure()
    #     tsat = n.get_refrigerant().t_sat(p)
    #     return tsat + tsh
    #
    # def _calculate_x0_TSC(self, nd_id: int, circuit: Circuit) -> float:
    #     tsc = self.get_property(nd_id, self.TSC)[0]
    #     n = circuit.get_node(nd_id)
    #     p = n.pressure()
    #     tsat = n.get_refrigerant().t_sat(p)
    #     return tsat - tsc

    def _calculate_x0_Qpower(self, nd_id: int, circuit: Circuit) -> float:
        prop = self.get_property(nd_id, self.Qpower)
        Q = prop[0]
        n1 = circuit.get_node(nd_id)
        h1 = n1.enthalpy()
        n2 = circuit.get_node(prop[1])
        h2 = n2.enthalpy()
        return abs(Q / (h2 - h1) * 1 / 1000)

    # Properties not supported because I don't know how to manage them in the ComplexPresolver:
    # def _calculate_x0_DP(self, nd_id: int, circuit: Circuit) -> float:
    #     prop = self.get_property(nd_id, self.DP)
    #     dp = prop[0]
    #     n2 = circuit.get_node(prop[1])
    #     p2 = n2.pressure()
    #     return p2 - dp
    #
    # def _calculate_x0_TDP(self, nd_id: int, circuit: Circuit) -> float:
    #     prop = self.get_property(nd_id, self.TDP)
    #     tdp = prop[0]
    #     n2 = circuit.get_node(prop[1])
    #     p2 = n2.pressure()
    #     tsat2 = n2.get_refigerant().t_sat(p2)
    #     tsat1 = tsat2 - tdp
    #     n1 = circuit.get_node(nd_id)
    #     return n1.get_refigerant().p_sat(tsat1)
    #
    # def _calculate_x0_DT(self, nd_id: int, circuit: Circuit) -> float:
    #     prop = self.get_property(nd_id, self.DP)
    #     dt = prop[0]
    #     n2 = circuit.get_node(prop[1])
    #     t2 = n2.temperature()
    #     return t2 - dt

    def serialize(self) -> dict:
        """
        Return a dict with the following structure:
        { node i identifier: {
            name of initial value: value,
            name of initial value: { value, node j identifier (node with it is related the initial value, node k,...),
            ...
            }
        ...
        """
        return {self.X0_DATA: self._nd}

    @staticmethod
    def deserialize(circuit_file: dict) -> object:
        refrigerant = circuit_file[ACircuitSerializer.REFRIGERANT]
        ref_lib = circuit_file[ACircuitSerializer.REF_LIB]
        x0_values = InitialValues(refrigerant, ref_lib)
        x0_data = circuit_file[x0_values.X0_DATA]
        for node in x0_data:
            data = x0_data[node]
            node = int(node)
            for prop in data:
                value = data[prop][0]
                external_nodes = data[prop][1:]
                x0_values.add(node, prop, value, *external_nodes)
        return x0_values
