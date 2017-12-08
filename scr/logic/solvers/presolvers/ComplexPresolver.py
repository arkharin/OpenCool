# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Presolver for complex circuits like two stage circuits but not for cascade systems.
"""

from scr.logic.solvers.presolvers.presolver import PreSolver
import scr.logic.nodes.node as nd
from scr.logic.components.component import ComponentInfo as CmpInfo
from scr.logic.errors import PreSolverError


class ComplexPresolver(PreSolver):
    # Directions to fill nodes
    _FORWARD = 'FORWARD'
    _BACKWARD = 'BACKWARD'
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
    _p = nd.Node.PRESSURE
    _h = nd.Node.ENTHALPY

    def calculate_initial_conditions(self, circuit):
        # Get components by type to use later.
        cps = circuit.get_components_by_type(self._COMPRESSOR)
        cds = circuit.get_components_by_type(self._CONDENSER)
        evs = circuit.get_components_by_type(self._EVAPORATOR)
        xvs = circuit.get_components_by_type(self._EXPANSION_VALVE)
        mfs = circuit.get_components_by_type(self._MIXER_FLOW)
        sfs = circuit.get_components_by_type(self._SEPARATOR_FLOW)
        tihtxs = circuit.get_components_by_type(self._TWO_INLET_HEAT_EXCHANGER)
        ots = circuit.get_components_by_type(self._OTHER)

        # Values to fill nodes later. Stored values are: Name physical property, value, Name physical property, value.
        # Mass flow values aren't inside of nodes, are in the circuit.
        nd_values = {x: [None] * 4 for x in circuit.get_nodes().keys()}

        # TODO Used initial values when are passed in _calculated_x_xx_xxxxx()
        # Fill nodes with pressure values.
        stop_cmps = {**cps, **cds, **evs, **xvs}  # Components to stop filling the line with the value indicated.
        nd_values = self._fill_nodes_with(circuit, nd_values, self._p, cds, stop_cmps, self._FORWARD,
                                          self._calculated_p_cd_forward, n_iteration=1)
        nd_values = self._fill_nodes_with(circuit, nd_values, self._p, cds, stop_cmps, self._BACKWARD,
                                          self._calculated_p_cd_backward, n_iteration=1)
        nd_values = self._fill_nodes_with(circuit, nd_values, self._p, evs, stop_cmps, self._FORWARD,
                                          self._calculated_p_ev_forward, n_iteration=1)
        nd_values = self._fill_nodes_with(circuit, nd_values, self._p, evs, stop_cmps, self._BACKWARD,
                                          self._calculated_p_ev_backward, n_iteration=1)
        nd_values = self._fill_nodes_with(circuit, nd_values, self._p, xvs, stop_cmps, self._FORWARD,
                                          self._calculated_p_xv_forward, n_iteration=1)

        # Fill nodes with enthalpy values.
        stop_cmps = {**cps, **cds, **evs, **mfs}  # Components to stop filling the line with the value indicated.
        nd_values = self._fill_nodes_with(circuit, nd_values, self._h, cds, stop_cmps, self._FORWARD,
                                          self._calculated_h_cd_forward, n_iteration=1)
        nd_values = self._fill_nodes_with(circuit, nd_values, self._h, cds, stop_cmps, self._BACKWARD,
                                          self._calculated_h_cd_backward, n_iteration=1)
        nd_values = self._fill_nodes_with(circuit, nd_values, self._h, evs, stop_cmps, self._FORWARD,
                                          self._calculated_h_ev_forward, n_iteration=1)
        nd_values = self._fill_nodes_with(circuit, nd_values, self._h, cps, stop_cmps, self._FORWARD,
                                          self._calculated_h_cp_forward, n_iteration=1)
        nd_values = self._fill_nodes_with(circuit, nd_values, self._h, cps, stop_cmps, self._BACKWARD,
                                          self._calculated_h_cp_backward, n_iteration=1)
        nd_values = self._fill_nodes_with(circuit, nd_values, self._h, mfs, stop_cmps, self._FORWARD,
                                          self._calculated_h_mf_forward, n_iteration=1)
        nd_values = self._fill_nodes_with(circuit, nd_values, self._h, mfs, stop_cmps, self._BACKWARD,
                                          self._calculated_h_mf_backward, n_iteration=1)

        # Update nodes with the calculated values.
        self._update_nodes(circuit.get_nodes(), nd_values)
        # Calculated mass flow values.
        # TODO change when default argument are supported.
        mass_flows = self._calculate_mass_flow(circuit)
        circuit.update_mass_flows(mass_flows)

        # Calculated node thermodynamic basic properties to pass and mass flows of the circuit to pass to the solver.
        initial_conditions = self._get_initial_conditions(circuit, mass_flows)
        # Check if all initial conditions are calculated.
        if self._are_initial_conditions_calculated(initial_conditions):
            return initial_conditions
        else:
            raise PreSolverError("Presolver didn't calculated a initial value for all nodes and mass flows.")

    def _fill_nodes_with(self, circuit, nd_values, physic_property, start_cmps, stop_cmps, direction, calc_value,
                         n_iteration=1):
        # Fill the physic property, like pressure or enthalpy, in nodes in the desired direction from a list of start
        # components until a stop_component is found. Number of iterations through all start components can be defined.
        # Same algorithm implemented in circuit method is_circuit_close but with option of the direction to traverse,
        # start with specific component and with the option to iterate. is_circuit_close is easier to understand.

        # List of nodes not filled already.
        n_not_filled = circuit.get_nodes_id()
        # Save the components id already traversed.
        cmp_explored = []
        # Iterated over start components until all nodes all filled or the number of iterations are reached.
        while n_iteration > 0:
            # Traverse all start components to fill nodes.
            for cmp_id in start_cmps:
                cmp_explored.append(cmp_id)
                # List for remember nodes to fill when there are more than one outlet(forward) or inlet(backward) node
                # in the component.
                if direction is self._FORWARD:
                    n_to_fill = circuit.get_component(cmp_id).get_id_outlet_nodes()
                elif direction is self._BACKWARD:
                    n_to_fill = circuit.get_component(cmp_id).get_id_inlet_nodes()
                else:
                    raise PreSolverError('Traverse direction for physic property' + str(
                        physic_property) + ' is not recognize. Direction = ' + str(direction))
                # Value to fill nodes.
                value = calc_value(circuit.get_component(cmp_id), circuit, nd_values)
                for n_id in n_to_fill:
                    n_not_filled.remove(n_id)
                    # Explore the node and advance to the next node to explore.
                    self._fill_next_nodes(n_id, circuit, cmp_explored, stop_cmps, n_not_filled, n_to_fill, nd_values,
                                          physic_property, value, direction)
                if len(n_not_filled) == 0:  # All nodes are filled now.
                    n_iteration = 0  # To finish the while True
                    break
            n_iteration -= 1

        return nd_values

    def _fill_next_nodes(self, n_id, circuit, cmp_explored, stop_cmps, n_not_filled, n_to_fill, nd_values,
                         physic_property, value, direction):
        # Fill a node, move to next component, move to one of the outlet (forward) or inlet(backward) node of the
        # component and save the others to fil they later.
        # Same algorithm implemented in circuit method _explore_node but with option of the direction to traverse and
        # fill the node. _explore_node is easier to understand.

        # If the node is filled, no need to fill it again and continue by this way.
        if not self._is_node_fill(n_id, physic_property, nd_values):
            self._store_value(physic_property, value, n_id, nd_values)
            cmps_attached = circuit.get_node(n_id).get_components_attached()
            # Get an arbitrary component. Can't be used .pop() because node object it's affected to.
            c = cmps_attached[0].get_id()
            if c in cmp_explored or c in stop_cmps:
                c = cmps_attached[1].get_id()
            if c not in cmp_explored and c not in stop_cmps:
                cmp_explored.append(c)
                if direction is self._FORWARD:
                    nodes_id = circuit.get_component(c).get_id_outlet_nodes()
                elif direction is self._BACKWARD:
                    nodes_id = circuit.get_component(c).get_id_inlet_nodes()
                else:
                    raise PreSolverError('Traverse direction for physic property' + str(
                        physic_property) + ' is not recognize. Direction = ' + str(direction))
                node_id = nodes_id.pop()
                n_not_filled.remove(node_id)
                n_to_fill += nodes_id
                self._fill_next_nodes(node_id, circuit, cmp_explored, stop_cmps, n_not_filled, n_to_fill, nd_values,
                                      physic_property, value, direction)

    def _is_node_fill(self, node_id, physic_property, nd_values):
        return physic_property in nd_values[node_id]

    def _store_value(self, physic_property, value, node_id, nd_values):
        if nd_values[node_id][0] is None:
            nd_values[node_id][0] = physic_property
            nd_values[node_id][1] = value
        elif nd_values[node_id][2] is None:
            nd_values[node_id][2] = physic_property
            nd_values[node_id][3] = value
        else:
            raise PreSolverError('All values of the node ' + str(node_id) + ' are already initialized')

    # Some values aren't used in all methods but are required for uniform API in _fill_nodes_with.
    def _calculated_p_cd_forward(self, condenser, circuit, nd_values, tc=318.15):
        # Calculated pressure for the condenser and nodes after it.
        # Use a initial value passed or one by default, condensation temperature = 45ºC.
        refrigerant = circuit.get_refrigerant()
        tmin = refrigerant.Tmin()
        tcritical = refrigerant.T_crit()
        if tc < tmin:
            tc = tmin + 0.1  # Temperature must be higher than Tmin.
        elif tc > tcritical:
            tc = tcritical
        return refrigerant.p(refrigerant.TEMPERATURE, tc, refrigerant.QUALITY, 0.0)

    def _calculated_p_cd_backward(self, condenser, circuit, nd_values, tc=318.15):
        # Calculated pressure for the condenser and nodes before it.
        # Use a initial value passed or one by default, condensation temperature = 45ºC.
        refrigerant = circuit.get_refrigerant()
        tmin = refrigerant.Tmin()
        tcritical = refrigerant.T_crit()
        if tc < tmin:
            tc = tmin + 0.1  # Temperature must be higher than Tmin.
        elif tc > tcritical:
            tc = tcritical
        return refrigerant.p(refrigerant.TEMPERATURE, tc, refrigerant.QUALITY, 1.0)

    def _calculated_p_ev_forward(self, evaporator, circuit, nd_values, te=263.15):
        # Calculated pressure for the evaporator and nodes after it.
        # Use a initial value passed or one by default, evaporation temperature = -10ºC.
        refrigerant = circuit.get_refrigerant()
        tmin = refrigerant.Tmin()
        tcritical = refrigerant.T_crit()
        if te < tmin:
            te = tmin + 0.1  # Temperature must be higher than Tmin.
        elif te > tcritical:
            te = tcritical
        return refrigerant.p(refrigerant.TEMPERATURE, te, refrigerant.QUALITY, 1.0)

    def _calculated_p_ev_backward(self, evaporator, circuit, nd_values, te=263.15):
        # Calculated pressure for the evaporator and nodes before it.
        # Use a initial value passed or one by default, evaporation temperature = -10ºC.
        refrigerant = circuit.get_refrigerant()
        tmin = refrigerant.Tmin()
        tcritical = refrigerant.T_crit()
        if te < tmin:
            te = tmin + 0.1  # Temperature must be higher than Tmin.
        elif te > tcritical:
            te = tcritical
        return refrigerant.p(refrigerant.TEMPERATURE, te, refrigerant.QUALITY, 0.0)

    def _calculated_p_xv_forward(self, expansion_valve, circuit, nd_values, te=273.15):
        # Calculated pressure for the expansion valves and nodes after it depending of the "attached" compressors.
        # When is a simple stage circuit is not required calculated any pressure.

        xv_id = expansion_valve.get_id()
        # Save the components id already explored.
        cmp_explored = [xv_id]
        # List for remember nodes to explore when there are more than one outlet node in a component.
        n_to_explore = expansion_valve.get_id_outlet_nodes()
        # Compressors in the circuit:
        compressors = circuit.get_components_by_type(self._COMPRESSOR)
        # Search compressors to calculated the intermediated pressure.
        # TODO With two stage compressor only one compressor is required.
        for n in n_to_explore:
            # Explore the node and advance to the next node to explore.
            nd_id_1, position_1 = self._search_compressor(n, circuit, cmp_explored, compressors, n_to_explore)
            if nd_id_1 is not None:
                break
        for n in n_to_explore:
            nd_id_2, position_2 = self._search_compressor(n, circuit, cmp_explored, compressors, n_to_explore)
            if position_2 != position_1:
                break
        if nd_id_1 is not None and nd_id_2 is not None:
            i = nd_values[nd_id_1].index(self._p)
            p1 = nd_values[nd_id_1][i + 1]
            i = nd_values[nd_id_2].index(self._p)
            p2 = nd_values[nd_id_2][i + 1]
            return (p1 * p2) ** 0.5
        else:
            return None

    def _search_compressor(self, n_id, circuit, cmp_explored, compressors, n_to_explore):
        # Return a node with a compressor and the possition (suction =0, discharge 1). If the branch has been explored,
        # return None.
        #
        # Explore a node, move to next component with this inlet node, move to one of the outlet node of the component
        # and save the other to explore they later.
        cmps_attached = circuit.get_node(n_id).get_components_attached()
        # Get an arbitrary component. Can't be used .pop() because node object it's affected to.
        c = cmps_attached[0].get_id()
        # If the component is already explored, finish the search.
        if c in cmp_explored:
            c = cmps_attached[1].get_id()
        # Check if it's a compressor.
        if c in compressors:
            if n_id in circuit.get_component(c).get_id_outlet_nodes():
                position = 0
            else:
                position = 1
            return n_id, position
        if c not in cmp_explored:
            cmp_explored.append(c)
            nodes_id = circuit.get_component(c).get_id_outlet_nodes()
            node_id = nodes_id.pop()
            n_to_explore += nodes_id
            self._search_compressor(node_id, circuit, cmp_explored, compressors, n_to_explore)
        # If the branch has been explored, return None.
        return None, None

    def _calculated_h_cd_forward(self, condenser, circuit, nd_values, tc=318.15):
        # Calculated enthalpy for the condenser and nodes after it.
        # Use a initial value passed or one by default, condensation temperature = 45ºC.
        refrigerant = circuit.get_refrigerant()
        tmin = refrigerant.Tmin()
        tcritical = refrigerant.T_crit()
        if tc < tmin:
            tc = tmin + 0.1  # Temperature must be higher than Tmin.
        elif tc > tcritical:
            tc = tcritical
        # Value of the initial subcooling is critical for the solver. In simple circuits, use a 0 subcooling leads to
        # find an incorrect solution when subcooling are low (for example 2ºC or 7ºC) due to the solver founds a local
        # minimum.
        return refrigerant.h(refrigerant.TEMPERATURE, tc - 10.0, refrigerant.QUALITY, 0.0)

    def _calculated_h_cd_backward(self, condenser, circuit, nd_values, tc=318.15):
        # Calculated enthalpy for the condenser and nodes after it.
        # Use a initial value passed or one by default, condensation temperature = 45ºC.
        refrigerant = circuit.get_refrigerant()
        tmin = refrigerant.Tmin()
        tcritical = refrigerant.T_crit()
        if tc < tmin:
            tc = tmin + 0.1  # Temperature must be higher than Tmin.
        elif tc > tcritical:
            tc = tcritical
        return refrigerant.h(refrigerant.TEMPERATURE, tc, refrigerant.QUALITY, 1.0)

    def _calculated_h_ev_forward(self, evaporator, circuit, nd_values, te=263.15):
        # Calculated enthalpy for the evaporator and nodes after it.
        # Use a initial value passed or one by default, evaporation temperature = -10ºC and superheat = 10ºC.
        refrigerant = circuit.get_refrigerant()
        tmin = refrigerant.Tmin()
        tcritical = refrigerant.T_crit()
        if te < tmin:
            te = tmin + 0.1  # Temperature must be higher than Tmin.
        elif te > tcritical:
            te = tcritical
        d = refrigerant.d(refrigerant.TEMPERATURE, te, refrigerant.QUALITY, 1.0)
        return refrigerant.h(refrigerant.TEMPERATURE, te + 10.0, refrigerant.DENSITY, d)

    def _calculated_h_cp_forward(self, compressor, circuit, nd_values):
        # Calculated enthalpy for the compressor and nodes of the discharge.
        # It's a isentropic compressor with isentropic efficiency = 1.
        inlet_node_id = compressor.get_id_inlet_nodes()[0]
        outlet_node_id = compressor.get_id_outlet_nodes()[0]
        try:
            i = nd_values[inlet_node_id].index(self._p)
        except ValueError:
            return None
        p_suction = nd_values[inlet_node_id][i + 1]
        try:
            i = nd_values[inlet_node_id].index(self._h)
        except ValueError:
            return None
        h_suction = nd_values[inlet_node_id][i + 1]
        try:
            i = nd_values[outlet_node_id].index(self._p)
        except ValueError:
            return None
        p_discharge = nd_values[outlet_node_id][i + 1]
        refrigerant = circuit.get_refrigerant()
        s_suction = refrigerant.s(refrigerant.PRESSURE, p_suction, refrigerant.ENTHALPY, h_suction)
        h_is = refrigerant.h(refrigerant.PRESSURE, p_discharge, refrigerant.ENTROPY, s_suction)
        return h_is

    def _calculated_h_cp_backward(self, compressor, circuit, nd_values):
        # Calculated enthalpy for the compressor and nodes of the discharge.
        # It's a isentropic compressor with isentropic efficiency = 1.
        inlet_node_id = compressor.get_id_inlet_nodes()[0]
        outlet_node_id = compressor.get_id_outlet_nodes()[0]
        try:
            i = nd_values[inlet_node_id].index(self._p)
        except ValueError:
            return None
        p_suction = nd_values[inlet_node_id][i + 1]
        try:
            i = nd_values[outlet_node_id].index(self._p)
        except ValueError:
            return None
        p_discharge = nd_values[outlet_node_id][i + 1]
        try:
            i = nd_values[outlet_node_id].index(self._h)
        except ValueError:
            return None
        h_discharge = nd_values[outlet_node_id][i + 1]
        refrigerant = circuit.get_refrigerant()
        # Approximated.
        s_discharge = refrigerant.s(refrigerant.PRESSURE, p_discharge, refrigerant.ENTHALPY, h_discharge)
        h_suction = refrigerant.h(refrigerant.PRESSURE, p_suction, refrigerant.ENTROPY, s_discharge)
        return h_suction

    def _calculated_h_mf_forward(self, mixer_flow, circuit, nd_values):
        # Calculated enthalpy for a mixer flow outlet outlet components
        inlet_nodes = mixer_flow.get_inlet_nodes()
        h_in = 0.0
        i = 0
        for node in inlet_nodes:
            node = circuit.get_node(node)
            node_id = node.get_id()
            try:
                h_in += nd_values[node_id].index(self._h)
                i += 1
            # No value in this node
            except ValueError:
                pass
        if i > 0:
            return h_in / i
        else:
            return None

    def _calculated_h_mf_backward(self, mixer_flow, circuit, nd_values):
        # Calculated enthalpy for a mixer flow outlet outlet components

        outlet_nodes = mixer_flow.get_outlet_nodes()
        h_out = 0
        i = 0
        for node in outlet_nodes:
            node = circuit.get_node(node)
            node_id = node.get_id()
            try:
                h_out += nd_values[node_id].index(self._h)
                i += 1
            # No value in this node
            except ValueError:
                pass
        if i > 0:
            return h_out / i
        else:
            return None

    def _calculate_mass_flow(self, circuit):
        cds = circuit.get_components_by_type(self._CONDENSER)
        evs = circuit.get_components_by_type(self._EVAPORATOR)
        mfs = circuit.get_components_by_type(self._MIXER_FLOW)
        sfs = circuit.get_components_by_type(self._SEPARATOR_FLOW)
        flow_components = {**mfs, **sfs}
        mass_flows = [None] * len(circuit.get_mass_flows())

        # TODO change when default argument are supported.
        for cd in cds:
            cd = circuit.get_component(cd)
            properties = cd.get_basic_properties()
            if 'heating_power' in properties:
                Q = cd.get_property('heating_power')
                id_inlet_node = cd.get_id_inlet_nodes()[0]
                inlet_node = cd.get_inlet_node(id_inlet_node)
                id_outlet_node = cd.get_id_outlet_nodes()[0]
                outlet_node = cd.get_outlet_node(id_outlet_node)
                h_in = inlet_node.enthalpy()
                h_out = outlet_node.enthalpy()
                mass_flow = Q / (h_in - h_out) * 1 / 1000
                id_mass_flow = inlet_node.get_id_mass_flow()
                if mass_flows[id_mass_flow] is None:
                    mass_flows[id_mass_flow] = mass_flow
                id_mass_flow = outlet_node.get_id_mass_flow()
                if mass_flows[id_mass_flow] is None:
                    mass_flows[id_mass_flow] = mass_flow

        for ev in evs:
            ev = circuit.get_component(ev)
            properties = ev.get_basic_properties()
            if 'cooling_power' in properties:
                Q = ev.get_property('cooling_power')
                id_inlet_node = ev.get_id_inlet_nodes()[0]
                inlet_node = ev.get_inlet_node(id_inlet_node)
                id_outlet_node = ev.get_id_outlet_nodes()[0]
                outlet_node = ev.get_outlet_node(id_outlet_node)
                h_in = inlet_node.enthalpy()
                h_out = outlet_node.enthalpy()
                mass_flow = Q / (h_out - h_in) * 1 / 1000
                id_mass_flow = inlet_node.get_id_mass_flow()
                if mass_flows[id_mass_flow] is None:
                    mass_flows[id_mass_flow] = mass_flow
                id_mass_flow = outlet_node.get_id_mass_flow()
                if mass_flows[id_mass_flow] is None:
                    mass_flows[id_mass_flow] = mass_flow

        for flow_component in flow_components:
            flow_component = circuit.get_component(flow_component)
            inlet_nodes = flow_component.get_inlet_nodes()
            in_m = [mass_flows[x.get_id_mass_flow()] for x in inlet_nodes.values()]
            outlet_nodes = flow_component.get_outlet_nodes()
            out_m = [mass_flows[x.get_id_mass_flow()] for x in outlet_nodes.values()]

            if None not in in_m and None in out_m:
                m = 0
                j = 0
                for i in in_m:
                    m += i
                for i in out_m:
                    if i is not None:
                        m -= i
                        j += 1
                m /= (len(out_m) - j)
                for outlet_node in outlet_nodes:
                    outlet_node = circuit.get_node(outlet_node)
                    id_mass_flow = outlet_node.get_id_mass_flow()
                    if mass_flows[id_mass_flow] is None:
                        mass_flows[id_mass_flow] = mass_flow

            if None not in out_m and None in in_m:
                m = 0
                j = 0
                for i in out_m:
                    m += i
                for i in in_m:
                    if i is not None:
                        m -= i
                        j += 1
                m /= (len(in_m) - j)
                for inlet_node in inlet_nodes:
                    inlet_node = circuit.get_node(inlet_node)
                    id_mass_flow = inlet_node.get_id_mass_flow()
                    if mass_flows[id_mass_flow] is None:
                        mass_flows[id_mass_flow] = mass_flow

        return mass_flows

    # _get_initial_conditions, _update_nodes, _are_initial_conditions_calculated may be reuse in other presolvers.
    def _get_initial_conditions(self, circuit, mass_flows):
        initial_conditions = []
        nodes = circuit.get_nodes()
        for node in nodes:
            node = nodes[node]
            initial_conditions.append(node.get_value_property_base_1())
            initial_conditions.append(node.get_value_property_base_2())
        for m_flow in mass_flows:
            initial_conditions.append(m_flow)
        return initial_conditions

    def _update_nodes(self, nodes, values):
        for n in nodes:
            node = nodes[n]
            n_values = values[n]
            node.update_node_values(n_values[0], n_values[1], n_values[2], n_values[3])

    def _are_initial_conditions_calculated(self, initial_conditions):
        for initial_condition in initial_conditions:
            if initial_condition is None:
                return False
        return True
