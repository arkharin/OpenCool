# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Presolver for complex circuits like two stage circuits but not for cascade systems.
"""

from scr.logic.solvers.presolvers.presolver import PreSolver
from scr.logic.components.component import ComponentInfo as CmpInfo
from scr.logic.errors import SolverError
from scr.logic.nodes.node import NodeInfo as NdInfo
from scr.logic.circuit import Circuit
from scr.logic.initial_values import InitialValues
from typing import List, Union, Callable, Optional
import logging as log


class ComplexPresolver(PreSolver):
    """
    Presolver for al kind of closed circuits not attached to other circuits.
    """
    # Directions to fill nodes
    _FWD = 'FORWARD'
    _BWD = 'BACKWARD'
    # Component types supported
    _COMPRESSOR = CmpInfo.COMPRESSOR
    _CONDENSER = CmpInfo.CONDENSER
    _EVAPORATOR = CmpInfo.EVAPORATOR
    _EXPANSION_VALVE = CmpInfo.EXPANSION_VALVE
    _MIXER_FLOW = CmpInfo.MIXER_FLOW
    _SEPARATOR_FLOW = CmpInfo.SEPARATOR_FLOW
    _TWO_INLET_HEAT_EXCHANGER = CmpInfo.TWO_INLET_HEAT_EXCHANGER
    _OTHER = CmpInfo.OTHER
    # Thermodynamic properties
    _P = NdInfo.PRESSURE
    _T = NdInfo.TEMPERATURE
    _H = NdInfo.ENTHALPY
    _D = NdInfo.DENSITY
    _S = NdInfo.ENTROPY
    _Q = NdInfo.QUALITY

    _M = NdInfo.MASS_FLOW

    def __init__(self, default_tc: float = 318.15, default_tsc: float = 10.0, default_te: float = 263.15,
                 default_tsh: float = 10.0) -> None:
        """Init of class. Default values used in default initial values calculation can be changed.
        :param default_tc: Condensation temperature for default initial values. Default= 45ºC.
        :param default_tsc: Subcooling for default initial values. Default= 10.0ºC. Initial subcooling
            is critical for the solver. In simple circuits, use a 0 subcooling leads to find an incorrect solution when
            subcooling are low (for example 2ºC or 7ºC) due to the solver founds a local minimum.
        :param default_te: Evaporation temperature for default initial values. Default= -10ºC.
        :param default_tsh:Superheat  for default initial values. Default= 10ºC.
        """
        self._circuit = None
        self._userx0 = None
        self._nd_values = None
        self._mass_flows = None
        self._node_with_x0_found = False

        # Default values to use when default values are calculated.
        self._default_tc = default_tc
        self._default_tsc = default_tsc
        self._default_te = default_te
        self._default_tsh = default_tsh

        super().__init__()

    def calculate_initial_conditions(self, circuit: Circuit, user_initial_values: InitialValues = None) -> List[float]:
        """Calculate initial values of a circuit."""
        self._circuit = circuit
        self._userx0 = user_initial_values
        # Get components by type to use later.
        cps = circuit.get_components_by_type(self._COMPRESSOR)
        cds = circuit.get_components_by_type(self._CONDENSER)
        evs = circuit.get_components_by_type(self._EVAPORATOR)
        xvs = circuit.get_components_by_type(self._EXPANSION_VALVE)
        mfs = circuit.get_components_by_type(self._MIXER_FLOW)
        sfs = circuit.get_components_by_type(self._SEPARATOR_FLOW)
        tihtxs = circuit.get_components_by_type(self._TWO_INLET_HEAT_EXCHANGER)
        ots = circuit.get_components_by_type(self._OTHER)

        # Components to stop filling the line with the value indicated.
        stop_cmps = {self._P: {**cps, **cds, **evs, **xvs}}
        stop_cmps[self._T] = {**cps, **cds, **evs, **xvs, **tihtxs}
        stop_cmps[self._H] = {**cps, **cds, **evs, **mfs}  # Approximation, no enthalpy change in tihtxs.
        stop_cmps[self._D] = {**cps, **cds, **evs, **xvs, **tihtxs}
        stop_cmps[self._S] = {**cds, **evs, **xvs, **mfs, **tihtxs}
        stop_cmps[self._Q] = {**cps, **cds, **evs, **xvs, **tihtxs}
        stop_cmps[self._M] = {**mfs, **sfs}

        # Values to fill nodes later. Stored values are: Name physical property, value, Name physical property, value.
        self._nd_values = {x: [None] * 4 for x in circuit.get_nodes().keys()}
        # Initial properties from the user dependent of nodes values can't be calculated at this stage
        self._fill_with_initial_basic_properties_user_values(stop_cmps)
        self._fill_with_default_initial_values(cds, cps, evs, mfs, stop_cmps, xvs)
        # Update nodes with the calculated values.
        self._update_circuit_nodes()
        # TODO support advanced thermodynamic properties that depends of the value of other nodes or of the value of
        # the same node previously calculated. For example, subcooling.
        # As all circuit have an initial value, all initial properties from the user can be calculated.
        # self._fill_with_all_thermodynamic_basic_properties_user_values(stop_cmps)
        # self._fill_with_default_initial_values(cds, cps, evs, mfs, stop_cmps, xvs)

        # Calculated mass flow values.
        self._calculate_mass_flow()

        # Calculated node thermodynamic properties and mass flows of the circuit to pass to the solver.
        initial_conditions = self._get_initial_conditions()
        # Check if all initial conditions are calculated.
        if self._are_initial_conditions_calculated(initial_conditions):
            return initial_conditions
        else:
            msg = "Presolver didn't calculated a initial value for all nodes and mass flows."
            log.error(msg)
            raise SolverError(msg)

    def _fill_with_default_initial_values(self, cds, cps, evs, mfs, stop_cmps, xvs):
        # With pressure.
        self._fill_nodes_with(self._P, cds, stop_cmps[self._P], self._FWD, self._calculated_p_cd_forward,
                              self._is_node_fill)
        self._fill_nodes_with(self._P, cds, stop_cmps[self._P], self._BWD, self._calculated_p_cd_backward,
                              self._is_node_fill)
        self._fill_nodes_with(self._P, evs, stop_cmps[self._P], self._FWD, self._calculated_p_ev_forward,
                              self._is_node_fill)
        self._fill_nodes_with(self._P, evs, stop_cmps[self._P], self._BWD, self._calculated_p_ev_backward,
                              self._is_node_fill)
        self._fill_nodes_with(self._P, xvs, stop_cmps[self._P], self._FWD, self._calculated_p_xv_forward,
                              self._is_node_fill)
        # With enthalpy.
        self._fill_nodes_with(self._H, cds, stop_cmps[self._H], self._FWD, self._calculated_h_cd_forward,
                              self._is_node_fill)
        self._fill_nodes_with(self._H, cds, stop_cmps[self._H], self._BWD, self._calculated_h_cd_backward,
                              self._is_node_fill)
        self._fill_nodes_with(self._H, evs, stop_cmps[self._H], self._FWD, self._calculated_h_ev_forward,
                              self._is_node_fill)
        self._fill_nodes_with(self._H, cps, stop_cmps[self._H], self._FWD, self._calculated_h_cp_forward,
                              self._is_node_fill)
        self._fill_nodes_with(self._H, cps, stop_cmps[self._H], self._BWD, self._calculated_h_cp_backward,
                              self._is_node_fill)
        self._fill_nodes_with(self._H, mfs, stop_cmps[self._H], self._FWD, self._calculated_h_mf_forward,
                              self._is_node_fill)
        self._fill_nodes_with(self._H, mfs, stop_cmps[self._H], self._BWD, self._calculated_h_mf_backward,
                              self._is_node_fill)

    def _fill_with_initial_basic_properties_user_values(self, stop_cmps):
        """Fill nodes only with direct initial values except mass flow related properties"""
        if self._userx0 is not None:
            basic_p = self._userx0.get_basic_properties()
            for node_id in self._userx0.get_nodes_id():
                node = self._circuit.get_node(node_id)
                cmp_out = node.get_outlet_component_attached()
                cmp_in = node.get_inlet_component_attached()
                for prop in self._userx0.get(node_id):
                    if prop in basic_p:
                        prop_info = self._userx0.get_property_info(prop)
                        x0 = prop_info[2](node_id, self._circuit)
                        p = prop_info[1]
                        self._fill_nodes_with(prop_info[1], cmp_out, stop_cmps[p], self._FWD, x0,
                                              self._is_node_fill_with_x0)
                        self._fill_nodes_with(prop_info[1], cmp_in, stop_cmps[p], self._BWD, x0,
                                              self._is_node_fill_with_x0)

    # TODO support advanced thermodynamic properties
    # def _fill_with_all_thermodynamic_basic_properties_user_values(self, stop_cmps):
    #     """Fill nodes with all properties not related to mass flow
    #     All the circuit have initial values and node dependent properties can be calculated"""
    #     if self._userx0 is not None:
    #         for node_id in self._userx0.get_nodes_id():
    #             node = self._circuit.get_node(node_id)
    #             cmp_out = node.get_outlet_component_attached()
    #             cmp_in = node.get_inlet_component_attached()
    #             for prop in self.get(node_id):
    #                 prop_info = self._userx0.get_property_info()
    #                 x0 = prop_info[2](node_id, self._circuit)
    #                 self._fill_nodes_with(prop_info[1], cmp_out, stop_cmps[prop], self._FWD, x0,
    #                                           self._is_node_fill_with_x0)
    #                 self._fill_nodes_with(prop_info[1], cmp_in, stop_cmps[prop], self._BWD, x0,
    #                                           self._is_node_fill_with_x0)

    def _fill_nodes_with(self, physic_property: int, start_cmps: Union[dict, str], stop_cmps: Union[dict, str],
                         direction: str, calc_value: Union[Callable, float],
                         is_allowed_fill_next_node: Callable[..., bool], n_iteration: int = 1) -> None:
        """
        Fill with a physic property all nodes between start components until a stop component is found .

        Fill with a physic property, like pressure or enthalpy, all nodes in the desired direction from a list of start
        components until a stop_component is found. Can iterate over the circuit if it's required.

        The algorithm is calculated a value, fill the node and look for the attached components and their nodes. The
        same algorithm is implemented in circuit method is_circuit_close but the direction is always traverse, starts
        with specific component. is_circuit_close is easier to understand.

        :param physic_property: a thermodynamic property
        :param start_cmps: components where start to fill the nodes
        :param stop_cmps: components that stops to fill the nodes with a calculated value. start components are not
            stop_cmps by default
        :param direction: to outlet nodes = self._FWD or to inlet nodes = self._BWD
        :param calc_value: function that calculate de default value or a value.
        :param is_allowed_fill_next_node: function that return true if the next node can be filled. Else, false.
        :param n_iteration: number of iterations over start_cmps
        """
        # List of nodes not filled already.
        n_not_filled = self._circuit.get_nodes_id()
        # Save the components id already traversed.
        cmp_explored = []
        # Iterated over start components until all nodes all filled or the number of iterations are reached.
        if type(start_cmps) is not dict:
            start_cmps = {start_cmps.get_id(): start_cmps}
        while n_iteration > 0:
            # Traverse all start components to fill nodes.
            for cmp_id in start_cmps:
                self._node_with_x0_found = False
                n_to_fill_x0_founded = [self._node_with_x0_found]
                cmp_explored.append(cmp_id)
                # List for remember nodes to fill when there are more than one outlet(forward) or inlet(backward) node
                # in the component.
                if direction is self._FWD:
                    n_to_fill = self._circuit.get_component(cmp_id).get_id_outlet_nodes()
                elif direction is self._BWD:
                    n_to_fill = self._circuit.get_component(cmp_id).get_id_inlet_nodes()
                else:
                    log.warning(f"Traverse direction for physic property {physic_property} isn't recognize. Direction ="
                                f" {direction}")
                # Value to fill nodes.
                if callable(calc_value):
                    value = calc_value(self._circuit.get_component(cmp_id))
                else:
                    value = calc_value
                for n_id, x0_found in zip(n_to_fill, n_to_fill_x0_founded):
                    n_not_filled.remove(n_id)
                    self._node_with_x0_found = x0_found
                    # Explore the node and advance to the next node to explore.
                    self._fill_next_nodes(n_id, cmp_explored, stop_cmps, n_not_filled, n_to_fill, physic_property,
                                          value, direction, n_to_fill_x0_founded, is_allowed_fill_next_node, True)
                if len(n_not_filled) == 0:  # All nodes are filled now.
                    n_iteration = 0  # To finish the while True
                    break
            n_iteration -= 1

    def _fill_next_nodes(self, n_id, cmp_explored, stop_cmps, n_not_filled, n_to_fill,
                         physic_property, default_value, direction, n_to_fill_x0_founded, is_node_fill, is_start_node):
        """Fill the nodes.

        Fill a node, move to next component, move to one of the outlet (forward) or inlet(backward) node of the
        component and save the others to fill they later.

        The same algorithm implemented in circuit method _explore_node but with option of the direction to traverse.
        _explore_node is easier to understand.
        """
        # If the node is filled, no need to fill it again and continue by this way.
        if not is_node_fill(n_id, physic_property, is_start_node):
            value = self._calculate_value(n_id, default_value, physic_property)
            self._store_value(physic_property, value, n_id)
            cmps_attached = self._circuit.get_node(n_id).get_components_attached()
            # Get an arbitrary component. Can't be used .pop() because node object it's affected to.
            c = cmps_attached[0].get_id()
            if c in cmp_explored or c in stop_cmps:
                c = cmps_attached[1].get_id()
            if c not in cmp_explored and c not in stop_cmps:
                cmp_explored.append(c)
                if direction is self._FWD:
                    nodes_id = self._circuit.get_component(c).get_id_outlet_nodes()
                elif direction is self._BWD:
                    nodes_id = self._circuit.get_component(c).get_id_inlet_nodes()
                else:
                    msg = f"Traverse direction for physic property{physic_property} is not recognize. Direction = " \
                          f"{direction}"
                    log.error(msg)
                    raise SolverError(msg)
                node_id = nodes_id.pop()
                n_not_filled.remove(node_id)
                if len(nodes_id) > 0:
                    n_to_fill += nodes_id
                    n_to_fill_x0_founded += [self._node_with_x0_found] * len(nodes_id)
                self._fill_next_nodes(node_id, cmp_explored, stop_cmps, n_not_filled, n_to_fill, physic_property,
                                      default_value, direction, n_to_fill_x0_founded, is_node_fill, False)

    def _is_node_fill_with_x0(self, node_id, physic_property, is_start_node):
        """Check if node need to be filled with a value. Only used with _userx0 initialized.

        A node can be filled if: it hasn't a initial value of the same property; has a initial value with other property
        and previous nodes hasn't a initial value.
        """
        node_x0_props = self._userx0.get(node_id)
        if node_x0_props is not None:
            node_x0_equivalent_props = [self._userx0.get_property_info(i)[1] for i in node_x0_props]
            if physic_property in node_x0_equivalent_props:
                if is_start_node and not self._is_node_fill(node_id, physic_property, is_start_node):
                    return False
                else:
                    return True
            else:
                if len(node_x0_props) < 2 and self._node_with_x0_found:
                    return False
                elif len(node_x0_props) < 2 and not self._node_with_x0_found:
                    self._node_with_x0_found = True
                    return False
                else:
                    return True
        else:
            return False

    def _is_node_fill(self, node_id, physic_property, is_start_node):
        """ Check if node need to be filled with a value. Only use when _fill_with_default_initial_values."""
        return physic_property in self._nd_values[node_id]

    def _store_value(self, physic_property, value, node_id):
        if self._nd_values[node_id][0] is None:
            self._nd_values[node_id][0] = physic_property
            self._nd_values[node_id][1] = value
        elif self._nd_values[node_id][2] is None:
            self._nd_values[node_id][2] = physic_property
            self._nd_values[node_id][3] = value

    def _calculate_value(self, nd_id, default_value, prop):
        if prop is self._P:
            value = self._calculate_p_node(nd_id)
        elif prop is self._T:
            value = self._calculate_t_node(nd_id)
        elif prop is self._H:
            value = self._calculate_h_node(nd_id)
        elif prop is self._D:
            value = self._calculate_d_node(nd_id)
        elif prop is self._S:
            value = self._calculate_s_node(nd_id)
        elif prop is self._Q:
            value = self._calculate_q_node(nd_id)
        else:
            msg = f"ComplexPresolver: PropertyName {prop} isn't recognized."
            log.error(msg)
            raise SolverError(msg)

        if value is not None:
            return value
        else:
            return default_value

    def _calculate_p_node(self, nd_id):
        values = self._nd_values[nd_id]
        if self._P in values:
            i = self._nd_values[nd_id].index(self._P)
            return self._nd_values[nd_id][i + 1]
        elif None not in values:
            node = self._circuit.get_node(nd_id)
            node.update_node_values(values[0], values[1], values[2], values[3])
            return node.pressure()
        else:
            return None

    def _calculate_t_node(self, nd_id):
        if self._T in self._nd_values[nd_id]:
            i = self._nd_values[nd_id].index(self._T)
            return self._nd_values[nd_id][i + 1]
        else:
            values = self._nd_values[nd_id]
            if None not in values:
                node = self._circuit.get_node(nd_id)
                node.update_node_values(values[0], values[1], values[2], values[3])
                return node.temperature()
            else:
                return None

    def _calculate_h_node(self, nd_id):
        if self._H in self._nd_values[nd_id]:
            i = self._nd_values[nd_id].index(self._H)
            return self._nd_values[nd_id][i + 1]
        else:
            values = self._nd_values[nd_id]
            if None not in values:
                node = self._circuit.get_node(nd_id)
                node.update_node_values(values[0], values[1], values[2], values[3])
                return node.enthalpy()
            else:
                return None

    def _calculate_d_node(self, nd_id):
        if self._D in self._nd_values[nd_id]:
            i = self._nd_values[nd_id].index(self._D)
            return self._nd_values[nd_id][i + 1]
        else:
            values = self._nd_values[nd_id]
            if None not in values:
                node = self._circuit.get_node(nd_id)
                node.update_node_values(values[0], values[1], values[2], values[3])
                return node.density()
            else:
                return None

    def _calculate_s_node(self, nd_id):
        if self._S in self._nd_values[nd_id]:
            i = self._nd_values[nd_id].index(self._S)
            return self._nd_values[nd_id][i + 1]
        else:
            values = self._nd_values[nd_id]
            if None not in values:
                node = self._circuit.get_node(nd_id)
                node.update_node_values(values[0], values[1], values[2], values[3])
                return node.entropy()
            else:
                return None

    def _calculate_q_node(self, nd_id):
        if self._Q in self._nd_values[nd_id]:
            i = self._nd_values[nd_id].index(self._Q)
            return self._nd_values[nd_id][i + 1]
        else:
            values = self._nd_values[nd_id]
            if None not in values:
                node = self._circuit.get_node(nd_id)
                node.update_node_values(values[0], values[1], values[2], values[3])
                return node.quality()
            else:
                return None

    def _default_p(self, present_n_id, previous_n_id, tsat):
        """Return the value of the pressure of the node."""
        # Check information in the present node.
        # Check if the present node has de pressure, should mean that the path is already filled.
        if self._P in self._nd_values[present_n_id]:
            i = self._nd_values[present_n_id].index(self._P)
            return self._nd_values[present_n_id][i + 1]
        elif self._nd_values[present_n_id][1] is not None and self._nd_values[present_n_id][3] is not None:
            values = self._nd_values[previous_n_id]
            node = self._circuit.get_node(previous_n_id)
            node.update_node_values(values[0], values[1], values[2], values[3])
            return node.pressure()
        elif self._P in self._nd_values[previous_n_id]:
            i = self._nd_values[previous_n_id].index(self._P)
            return self._nd_values[previous_n_id][i + 1]
        elif self._nd_values[previous_n_id][1] is not None and self._nd_values[previous_n_id][3] is not None:
            values = self._nd_values[previous_n_id]
            node = self._circuit.get_node(previous_n_id)
            node.update_node_values(values[0], values[1], values[2], values[3])
            return node.pressure()
        else:
            refrigerant = self._circuit.get_refrigerant()
            tmin = refrigerant.Tmin()
            tcritical = refrigerant.T_crit()
            if tsat < tmin:
                tsat = tmin + 0.1  # Temperature must be higher than Tmin.
            elif tsat > tcritical:
                tsat = tcritical
            return refrigerant.p(refrigerant.TEMPERATURE, tsat, refrigerant.QUALITY, 0.0)

    def _calculated_p_cd_forward(self, condenser):
        """Calculated pressure for the condenser and nodes after it."""
        id_inlet_node = condenser.get_id_inlet_nodes()[0]
        id_outlet_node = condenser.get_id_outlet_nodes()[0]
        p_in = self._default_p(id_outlet_node, id_inlet_node, self._default_tc)
        return p_in

    def _calculated_p_cd_backward(self, condenser):
        """Calculated pressure for the condenser and nodes before it."""
        id_inlet_node = condenser.get_id_inlet_nodes()[0]
        id_outlet_node = condenser.get_id_outlet_nodes()[0]
        p_out = self._default_p(id_inlet_node, id_outlet_node, self._default_tc)
        return p_out

    def _calculated_p_ev_forward(self, evaporator):
        """Calculated pressure for the evaporator and nodes after it."""
        id_inlet_node = evaporator.get_id_inlet_nodes()[0]
        id_outlet_node = evaporator.get_id_outlet_nodes()[0]
        p_in = self._default_p(id_outlet_node, id_inlet_node, self._default_te)
        return p_in

    def _calculated_p_ev_backward(self, evaporator):
        """Calculated pressure for the evaporator and nodes before it."""
        id_inlet_node = evaporator.get_id_inlet_nodes()[0]
        id_outlet_node = evaporator.get_id_outlet_nodes()[0]
        p_out = self._default_p(id_inlet_node, id_outlet_node, self._default_te)
        return p_out

    def _calculated_p_xv_forward(self, expansion_valve):
        """Calculated pressure for the expansion valves and nodes after it.

        The pressure is depending of the "attached" compressors.When is a simple stage circuit is not required
        calculated any pressure.
        """
        xv_id = expansion_valve.get_id()
        # Save the components id already explored.
        cmp_explored = [xv_id]
        # List for remember nodes to explore when there are more than one outlet node in a component.
        n_to_explore = expansion_valve.get_id_outlet_nodes()
        # Compressors in the circuit:
        compressors = self._circuit.get_components_by_type(self._COMPRESSOR)
        # Search compressors to calculated the intermediated pressure.
        # TODO With two stage compressor only one compressor is required.
        for n in n_to_explore:
            # Explore the node and advance to the next node to explore.
            nd_id_1, position_1 = self._search_compressor(n, cmp_explored, compressors, n_to_explore)
            if nd_id_1 is not None:
                break
        for n in n_to_explore:
            nd_id_2, position_2 = self._search_compressor(n, cmp_explored, compressors, n_to_explore)
            if position_2 != position_1:
                break
        if nd_id_1 is not None and nd_id_2 is not None:
            p1 = self._calculate_p_node(nd_id_1)
            p2 = self._calculate_p_node(nd_id_2)
            return (p1 * p2) ** 0.5
        else:
            return None

    def _search_compressor(self, n_id, cmp_explored, compressors, n_to_explore) -> Optional[List[int]]:
        """Return a node with a compressor and the position.

        :return [node_id, postion]. Postion: suction =0, discharge 1. If the branch has been explored, return None.
        """
        #
        # Explore a node, move to next component with this inlet node, move to one of the outlet node of the component
        # and save the other to explore they later.
        cmps_attached = self._circuit.get_node(n_id).get_components_attached()
        # Get an arbitrary component. Can't be used .pop() because node object it's affected to.
        c = cmps_attached[0].get_id()
        # If the component is already explored, finish the search.
        if c in cmp_explored:
            c = cmps_attached[1].get_id()
        # Check if it's a compressor.
        if c in compressors:
            if n_id in self._circuit.get_component(c).get_id_outlet_nodes():
                position = 0
            else:
                position = 1
            return n_id, position
        if c not in cmp_explored:
            cmp_explored.append(c)
            nodes_id = self._circuit.get_component(c).get_id_outlet_nodes()
            node_id = nodes_id.pop()
            n_to_explore += nodes_id
            self._search_compressor(node_id, cmp_explored, compressors, n_to_explore)
        # If the branch has been explored, return None.
        return None, None

    def _default_h(self, n_id: int, tsat: float, Q: float, tsc: float=0.0, tsh: float=0.0) -> float:
        """Return the value of the enthalpy by default of a node
        :param n_id: node id in with look for the pressure.
        :param tsat: saturation temperature in Kelvin
        :param Q: quality to use if default value is in saturated state.
        :param tsc: subcooling in Kelvin.
        :param tsh: superheating in Kelvin.
        :return: enthalpy.
        """
        refrigerant = self._circuit.get_refrigerant()
        # Use the pressure if it's available.
        if self._P in self._nd_values[n_id]:
            i = self._nd_values[n_id].index(self._P)
            p = self._nd_values[n_id][i + 1]
            tsat = refrigerant.T_sat(p)
        elif self._nd_values[1] is not None and self._nd_values[3] is not None:
            values = self._nd_values[n_id]
            node = self._circuit.get_node(n_id)
            node.update_node_values(values[0], values[1], values[2], values[3])
            p = node.pressure()
            tsat = refrigerant.T_sat(p)
        else:
            p = refrigerant.p_sat(tsat)

        t = tsat - tsc + tsh
        tmin = refrigerant.Tmin()
        if t < tmin:
            t = tmin + 0.1  # Temperature must be higher than Tmin.

        if t == tsat:
            tcritical = refrigerant.T_crit()
            if tsat > tcritical:
                tsat = tcritical
            return refrigerant.h(refrigerant.TEMPERATURE, tsat, refrigerant.QUALITY, Q)
        else:
            return refrigerant.h(refrigerant.TEMPERATURE, t, refrigerant.PRESSURE, p)

    def _calculated_h_cd_forward(self, condenser):
        """Calculated enthalpy for the condenser and nodes after it."""
        id_outlet_node = condenser.get_id_outlet_nodes()[0]
        h_out = self._default_h(id_outlet_node, self._default_tc, 0.0, tsc=self._default_tsc)
        return h_out

    def _calculated_h_cd_backward(self, condenser):
        """Calculated enthalpy for the condenser and nodes after it."""
        id_inlet_node = condenser.get_id_inlet_nodes()[0]
        h_in = self._default_h(id_inlet_node, self._default_tc, 1.0, tsh=self._default_tsh)
        return h_in

    def _calculated_h_ev_forward(self, evaporator):
        """Calculated enthalpy for the evaporator and nodes after it."""
        id_outlet_node = evaporator.get_id_outlet_nodes()[0]
        h_out = self._default_h(id_outlet_node, self._default_te, 1.0, tsh=self._default_tsh)
        return h_out

    def _calculated_h_cp_forward(self, compressor):
        """Calculated enthalpy for the compressor and nodes of the discharge."""
        # It's a isentropic compressor with isentropic efficiency = 1.
        inlet_node_id = compressor.get_id_inlet_nodes()[0]
        outlet_node_id = compressor.get_id_outlet_nodes()[0]
        p_suction = self._calculate_p_node(inlet_node_id)
        h_suction = self._calculate_h_node(inlet_node_id)
        p_discharge = self._calculate_p_node(outlet_node_id)
        refrigerant = self._circuit.get_refrigerant()
        if None not in [p_suction, h_suction, p_discharge]:
            s_suction = refrigerant.s(refrigerant.PRESSURE, p_suction, refrigerant.ENTHALPY, h_suction)
            h_is = refrigerant.h(refrigerant.PRESSURE, p_discharge, refrigerant.ENTROPY, s_suction)
            return h_is
        else:
            return None

    def _calculated_h_cp_backward(self, compressor):
        """Calculated enthalpy for the compressor and nodes of the discharge."""
        # It's a isentropic compressor with isentropic efficiency = 1.
        inlet_node_id = compressor.get_id_inlet_nodes()[0]
        outlet_node_id = compressor.get_id_outlet_nodes()[0]
        p_suction = self._calculate_p_node(inlet_node_id)
        p_discharge = self._calculate_p_node(outlet_node_id)
        h_discharge = self._calculate_h_node(outlet_node_id)
        refrigerant = self._circuit.get_refrigerant()
        if None not in [p_suction, p_discharge, h_discharge]:
            # Approximated.
            s_discharge = refrigerant.s(refrigerant.PRESSURE, p_discharge, refrigerant.ENTHALPY, h_discharge)
            h_suction = refrigerant.h(refrigerant.PRESSURE, p_suction, refrigerant.ENTROPY, s_discharge)
            return h_suction
        else:
            return None

    def _calculated_h_mf_forward(self, mixer_flow):
        """Calculated enthalpy for a mixer flow outlet outlet components"""
        inlet_nodes = mixer_flow.get_inlet_nodes()
        h_in = 0.0
        i = 0
        for node in inlet_nodes:
            node = self._circuit.get_node(node)
            node_id = node.get_id()
            h_node = self._calculate_h_node(node_id)
            if h_node is not None:
                h_in += h_node
                i += 1
        if i > 0:
            return h_in / i
        else:
            return None

    def _calculated_h_mf_backward(self, mixer_flow):
        """Calculated enthalpy for a mixer flow outlet outlet components"""
        outlet_nodes = mixer_flow.get_outlet_nodes()
        h_out = 0
        i = 0
        for node in outlet_nodes:
            node = self._circuit.get_node(node)
            node_id = node.get_id()
            h_node = self._calculate_h_node(node_id)
            if h_node is not None:
                h_out += h_node
                i += 1
        if i > 0:
            return h_out / i
        else:
            return None

    def _calculate_mass_flow(self):
        cds = self._circuit.get_components_by_type(self._CONDENSER)
        evs = self._circuit.get_components_by_type(self._EVAPORATOR)
        mfs = self._circuit.get_components_by_type(self._MIXER_FLOW)
        sfs = self._circuit.get_components_by_type(self._SEPARATOR_FLOW)
        flow_components = {**mfs, **sfs}
        self._mass_flows = [None] * len(self._circuit.get_mass_flows())

        # Initial mass flow calculations
        if self._userx0 is not None:
            m_p = self._userx0.get_mass_flow_properties()
            for node_id in self._userx0.get_nodes_id():
                for prop in self._userx0.get(node_id):
                    if prop in m_p:
                        node = self._circuit.get_node(node_id)
                        prop_info = self._userx0.get_property_info(prop)
                        m0 = prop_info[2](node_id, self._circuit)
                        id_mass_flow = node.get_id_mass_flow()
                        if self._mass_flows[id_mass_flow] is None:
                            self._mass_flows[id_mass_flow] = m0
                        else:
                            raise log.warning(f"Node {node_id} has already an initial mass flow. New mass flow won't be"
                                              f" used.")
        if self._mass_flows.count(None) == len(self._mass_flows):
            node = self._circuit.get_node()
            id_mass_flow = node.get_id_mass_flow()
            self._mass_flows[id_mass_flow] = 10 / 3600  # Default value, 10 kg/h

        # Initial mass flow calculations when there are a mixer and separator flow components
        iterations = 1
        while iterations > 0:
            if iterations > 1000:
                msg = "Mass flows calculation in ComplexPresolver is not converging."
                log.error(msg)
                raise SolverError(msg)
            iterations -= 1
            for flow_component in flow_components:
                flow_component = self._circuit.get_component(flow_component)
                inlet_nodes = flow_component.get_inlet_nodes()
                in_m = [self._mass_flows[x.get_id_mass_flow()] for x in inlet_nodes.values()]
                outlet_nodes = flow_component.get_outlet_nodes()
                out_m = [self._mass_flows[x.get_id_mass_flow()] for x in outlet_nodes.values()]
                if None in in_m or None in out_m:
                    total_mi = self._sum_mass_flows(in_m)
                    total_mo = self._sum_mass_flows(out_m)
                    if total_mi == 0.0 and total_mo == 0.0:
                        # Try to calculate values later
                        iterations += 1
                    elif total_mi > total_mo:
                        self._calculated_and_fill_mass_flow_of_flow_components(in_m, inlet_nodes, out_m, outlet_nodes)
                    else:
                        self._calculated_and_fill_mass_flow_of_flow_components(out_m, outlet_nodes, in_m, inlet_nodes)

    def _sum_mass_flows(self, mass_flows: List[float]) -> float:
        m_total = 0.0
        if None not in mass_flows:
            m_total = sum(mass_flows)
        else:
            for m in mass_flows:
                if m is not None:
                    m_total += m
        return m_total

    def _calculated_and_fill_mass_flow_of_flow_components(self, m_1, nodes_1, m_2, nodes_2):
        """Calculate the mass flow for the flow components depending of the known values."""
        i = 0
        total_m_1 = 0.0
        for m in m_1:
            if m is None:
                i += 1
            else:
                total_m_1 += m
        if i > 0:
            m1 = total_m_1 / i
            for node in nodes_1:
                if self._mass_flows[nodes_1[node].get_id_mass_flow()] is None:
                    self._mass_flows[nodes_1[node].get_id_mass_flow()] = m1
            total_m_1 += m1 * i
        j = 0
        total_m_2 = 0.0
        for m in m_2:
            if m is None:
                j += 1
            else:
                total_m_2 += m
        m2 = (total_m_1 - total_m_2) / j
        for node in nodes_2:
            if self._mass_flows[nodes_2[node].get_id_mass_flow()] is None:
                self._mass_flows[nodes_2[node].get_id_mass_flow()] = m2

    # _get_initial_conditions, _are_initial_conditions_calculated may be reuse in other presolvers.
    def _get_initial_conditions(self) -> List[float]:
        """Return a list with the values for the initial conditions for the solver algorithm"""
        initial_conditions = []
        nodes = self._circuit.get_nodes()
        for node in nodes:
            node = nodes[node]
            initial_conditions.append(node.get_value_property_base_1())
            initial_conditions.append(node.get_value_property_base_2())
        for m_flow in self._mass_flows:
            initial_conditions.append(m_flow)
        return initial_conditions

    def _update_circuit_nodes(self):
        """Calculate base properties of all circuit nodes."""
        values = self._nd_values
        nodes = self._circuit.get_nodes()
        for n in nodes:
            node = nodes[n]
            n_values = values[n]
            node.update_node_values(n_values[0], n_values[1], n_values[2], n_values[3])

    def _are_initial_conditions_calculated(self, initial_conditions):
        for initial_condition in initial_conditions:
            if initial_condition is None:
                return False
        return True
