#!/usr/bin/python3
"""Module containing the FPSelect lattice search algorithm."""

import json
from datetime import datetime, timedelta

from loguru import logger
from sortedcontainers import SortedDict

from fpselect.attribute import Attribute
from fpselect.cost import Cost, CostFunction
from fpselect.sensitivity import SensitivityFunction


class FPSelect:
    """The FPSelect class containing the algorithm."""

    def __init__(self, candidate_attributes: set[Attribute],
                 sensitivity_threshold: float, explored_paths: int,
                 cost_function: CostFunction,
                 sensitivity_function: SensitivityFunction,
                 pruning: bool = True, save_data: bool = False,
                 save_path: str = 'fpselect.json'):
        """Initializes the FPSelect algorithm with the functions.

        Args:
            candidate_attributes: The set of the candidate attributes.
            sensitivity_threshold: The sensitivity threshold.
            explored_paths: The number of explored paths.
            cost_function: The cost function to measure the cost of the
              attribute sets.
            sensitivity_function: The sensitivity function to measure the
              sensitivity of the attribute sets.
            pruning: Whether we use the pruning methods.
            save_data: Whether to save the exploration data or not.
            save_path: The path to where write the json result file.
        """
        # Initializes the parameters of the algorithm
        self._candidate_attributes = candidate_attributes
        self._sensitivity_threshold = sensitivity_threshold
        self._explored_paths = explored_paths
        self._cost_function = cost_function
        self._sensitivity_function = sensitivity_function
        self._pruning = pruning
        self._save_data = save_data
        self._save_path = save_path

        # Some info/debug messages
        logger.info('Initialized FPSelect with %d candidate attributes'
                    % len(self._candidate_attributes))
        logger.debug('The candidate attributes: %s'
                     % self._candidate_attributes)
        logger.info('FPSelect is parametered with a threshold of %f'
                    % self._sensitivity_threshold)
        logger.info('FPSelect is parametered to explore %d paths'
                    % self._explored_paths)
        logger.info('FPSelect is parametered to%s use the pruning methods'
                    % '' if self._pruning else ' NOT')
        if self._save_data:
            logger.info('FPSelect is parametered to save the data to %s'
                        % self._save_path)
        logger.debug('The cost function used is %s' % self._cost_function)
        logger.debug('The sensitivity function used is %s'
                     % self._sensitivity_function)


    def run(self):
        """Runs the FPSelect lattice search algorithm.
        """
        logger.info("Starting the FPSelect lattice search algorithm...")

        # First, prepare the variables used during the exploration
        self._prepare_exploration()

        # Then, check that the sensitivity threshold is reachable
        if not self._is_sensitivity_threshold_reachable():
         logger.warning('The sensitivity threshold is not reachable even '
                        'using all the candidate attributes')
         return None

        # If a solution exists, process to the lattice exploration
        self._explore_lattice()

        # Save the data if asked to
        if self._save_data:
            self._save_exploration_data()


    def get_solution(self) -> set[Attribute]:
        """Gives the solution found by FPSelect.

        Returns:
            The attribute sets that satisfies the sensitivity threshold at the
            lowest cost, or None if none satisfies the sensitivity threshold.
        """
        return self._best_attr_set


    def get_satisfying_attribute_sets(self) -> set[set[Attribute]]:
        """Gives the attribute sets that satisfy the sensitivity threshold.

        Returns:
            The attribute sets that satisfy the sensitivity threshold which were
            encountered during the exploration.
        """
        return self._t_satisfy_sens_thresh


    def _prepare_exploration(self):
        """Initializes the variables used during the exploration."""
        # Storage for the explored attribute sets (in the order of exploration)
        self._explored_sets = []

        # The maximum cost when considering the complete set of attributes
        self._max_cost = self._cost_function.measure(self._candidate_attributes)

        # The minimum cost and the less costly attribute set currently found
        self._min_cost = Cost(float('inf'), None)
        self._best_attr_set = None

        # The set S of the attribute sets to expand, initialized to k empty sets
        self._s_to_expand = set(frozenset()
                                for _ in range(self._explored_paths))

        # The set T of the attribute sets that reached the sensitivity threshold
        self._t_satisfy_sens_thresh = set()

        # The set I of the attributes which supersets should not be explored
        self._i_ignored_supersets = set()

        # A timer to hold the starting time of the algorithm
        self._start_time = datetime.now()


    def _is_sensitivity_threshold_reachable(self):
        """Checks that the sensitivity is reachable using all the attributes.

        It computes the minimum sensitivity obtained when considering all the
        attributes, and checks whether this minimum is below the sensitivity
        threshold. If it is not, no solution exists as all the attribute
        subsets will show a higher sensitivity.

        Returns:
            If the sensitivity threshold is reachable.
        """
        # Compute the sensitivity considering the complete set of attributes
        sens_cand_attrs = self._sensitivity_function.measure(
            self._candidate_attributes)
        cost_cand_attrs = self._cost_function.measure(
            self._candidate_attributes)

        # Store this attribute set in the explored sets
        compute_time = datetime.now() - self._start_time
        self._explored_sets.append((compute_time, self._candidate_attributes,
                                    sens_cand_attrs, cost_cand_attrs))

        # Return whether this minimum sensitivity is below the threshold
        return (sens_cand_attrs <= self._sensitivity_threshold)


    def _explore_lattice(self):
        """Explores the lattice according to the FPSelect algorithm."""
        # While the set S is not empty, we continue the exploration. Note that
        # it is initialized to k empty sets.
        while len(self._s_to_expand) > 0:

            # Generate the attr. sets to explore by expanding the set S
            sets_to_explore = self._expand_s()

            # Hold the next attr. sets to expand sorted by their efficiency
            next_attr_sets_to_expand = SortedDict()

            # For each attribute set to explore  (for C in E)
            for attr_set in sets_to_explore:

                # Compute its sensitivity and its cost
                sensitivity = self._sensitivity_function.measure(attr_set)
                cost = self._cost_function.measure(attr_set)

                # Store this attribute set in the explored sets
                compute_time = datetime.now() - self._start_time
                self._explored_sets.append(
                    (compute_time, attr_set, sensitivity, cost))

                # If the sensitivity threshold is reached  (s(C) <= alpha)
                if sensitivity <= self._sensitivity_threshold:
                    self._t_satisfy_sens_thresh.add(attr_set)

                    # If a minimum cost is found  (c(C) < c_min)
                    if cost.get_value() < self._min_cost.get_value():
                        self._min_cost = cost
                        self._best_attr_set = attr_set

                # If the sensitivity threshold is not reached but the cost is
                # still below the minimum currently found
                # (s(C) > alpha) && (c(C) < c_min)
                elif cost.get_value() < self._min_cost.get_value():
                    # Compute the efficiency of this attribute set
                    cost_gain = self._max_cost.get_value() - cost.get_value()
                    efficiency = cost_gain / sensitivity

                    # Add this attribute to the next attr. sets to expand
                    next_attr_sets_to_expand[efficiency] = attr_set

                # For any other cases (threshold not reached, higher cost) when
                # the pruning methods are used
                elif self._pruning:
                    self._i_ignored_supersets.add(attr_set)

            # Clear the sets to expand to store the ones if there are some
            self._s_to_expand.clear()

            # After having explored all the attribute sets, get the k most
            # efficient attr. sets that are the next to explore
            for _ in range(min(self._explored_paths,
                               len(next_attr_sets_to_expand))):
                most_efficient_attr_set = next_attr_sets_to_expand.popitem(-1)
                self._s_to_expand.add(most_efficient_attr_set)

        # A little message when the exploration is done
        diff_w_start_time = datetime.now() - self._start_time
        logger.info('The exploration is done after %s' % diff_w_start_time)
        logger.info('%d attribute sets were explored, among which %d satisfy '
                    'the sensitivity threshold' %
                    (len(self._explored_sets),
                     len(self._t_satisfy_sens_thresh)))


    def _expand_s(self):
        """Expand the set S to obtain the attribute sets to explore.

        For each S_i of S, we generate the attribute sets to explore that are composed of each S_i with one more attribute that is not already in S_i.
        E <-- {C = S_i Union {a} :
               For all S_i \in S, For all a \in A, a Not in S_i}

        We do not hold C in E if:
        - It is a superset of an attr. set of T (i.e., if it is a superset of
          an attr. set that satisfies the sensitivity threshold).
        - The pruning methods are used and C is a superset of the attr. sets
          whose supersets are to be ignored.

        Returns:
            The set E of the next attribute sets to explore.
        """
        # The set E of the attribute sets to explore
        attr_sets_to_explore = set()

        # Generate the attr. sets composed of S_i with one more attr.
        for set_to_expand in self._s_to_expand:  # For all S_i in S
            for attribute in self._candidate_attributes:  # For all a in A

                # The attr. set C with one more attribute (S_i union {a})
                new_attr_set = set_to_expand.union(set([attribute]))

                # Ignore C if the attr. a is already in the attr. set S_i
                if attribute in set_to_expand:
                    continue

                # Ignore C if it is a superset of an attr. set of T
                for attr_set_sat in self._t_satisfy_sens_thresh:
                    if new_attr_set.issuperset(attr_set_sat):
                        continue

                # Ignore C if we use the pruning methods and it is a superset
                # of an attr. set which supersets are to be ignored
                if self._pruning:
                    for attr_set_to_ign in self._i_ignored_supersets:
                        if new_attr_set.issuperset(attr_set_to_ign):
                            continue

                # If C is fine, it is added to the attr. sets to explore
                attr_sets_to_explore.add(new_attr_set)

        # Return the set E of the attribute sets to explore
        return attr_sets_to_explore


    def _save_exploration_data(self):
        """Save the exploration data in the form of a json file."""
        # The json dictionary to save (as a python dict)
        json_output = {}

        # Put the attributes in it
        json_output['attributes'] = {}
        for attribute in self._candidate_attributes:
            json_output['attributes'][attribute.get_id()] = attribute.get_name()

        # Put the explored attribute sets
        json_output['exploration'] = {}
        for id, explr_set_information in enumerate(self._explored_sets):
            time_delta, attr_set, sensitivity, cost = explr_set_information
            data = {
                'seconds': time_delta.total_seconds(),
                'attributes': [attr.get_id() for attr in attr_set],
                'sensitivity': sensitivity,
                'cost': cost.get_value(),
                'cost_description': cost.get_description()
            }
            json_output['exploration'][id] = data

        # Save the exploration data as a json file
        with open(self._save_path, 'w+') as save_file:
            json.dump(json_output, save_file)
