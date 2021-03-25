#!/usr/bin/python3
"""Module containing the FPSelect exploration algorithm."""

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, Optional, Set

from loguru import logger
from sortedcontainers import SortedDict

from brfast.exploration import (Exploration, ExplorationParameters, State,
                                TraceData)
from brfast.data import AttributeSet, FingerprintDataset
from brfast.measures import SensitivityMeasure, UsabilityCostMeasure


class FPSelectParameters(ExplorationParameters):
    """Class representing the parameters of the FPSelect exploration alg."""

    EXPLORED_PATHS = 'explored_paths'
    PRUNING = 'pruning'


class FPSelect(Exploration):
    """The implementation of the FPSelect exploration algorithm."""

    def __init__(self, sensitivity_measure: SensitivityMeasure,
                 usability_cost_measure: UsabilityCostMeasure,
                 dataset: FingerprintDataset, sensitivity_threshold: float,
                 explored_paths: int, pruning: bool):
        """Initialize the FPSelect exploration algorithm.

        Args:
            sensitivity_measure: The sensitivity measure.
            usability_cost_measure: The usability cost.
            dataset: The fingerprint dataset.
            sensitivity_threshold: The sensivity threshold.
            explored_paths: The number of paths explored by FPSelect.
            pruning: Use the pruning methods.
        """
        # Initialize using the __init__ function of Exploration
        super().__init__(sensitivity_measure, usability_cost_measure, dataset,
                         sensitivity_threshold)

        # Check the number of explored paths
        if explored_paths < 1:
            raise AttributeError()

        # Initialize the specific parameters of FPSelect
        self._explored_paths = explored_paths
        self._pruning = pruning
        logger.info(f'Initialized FPSelect with {explored_paths} paths to '
                    'explore.')
        if pruning:
            logger.info('Pruning methods are activated.')
        else:
            logger.info('Pruning methods are ignored.')

        # Initialize the best solution and the minimum cost currently found
        self._solution, self._min_cost = None, float('inf')

        # The set S of the attributes set to expand at each step, initialized
        # to k empty sets
        self._attr_sets_to_expand = set(AttributeSet()
                                        for _ in range(self._explored_paths))

        # The set I of the attribute sets which supersets are to ignore
        self._attr_sets_ignored_supersets = set()

    @property
    def parameters(self) -> Dict[str, Any]:
        """Give the parameters of the exploration as a dictionary.

        Returns:
            The parameters as a dictionary of their name and their value.
        """
        return {
            ExplorationParameters.METHOD: self.__class__.__name__,
            ExplorationParameters.SENSITIVITY_MEASURE: str(self._sensitivity),
            ExplorationParameters.USABILITY_COST_MEASURE: str(
                self._usability_cost),
            ExplorationParameters.DATASET: str(self._dataset),
            ExplorationParameters.SENSITIVITY_THRESHOLD: (
                self._sensitivity_threshold),
            FPSelectParameters.EXPLORED_PATHS: self._explored_paths,
            FPSelectParameters.PRUNING: self._pruning
        }

    def _search_for_solution(self):
        """Search for a solution using the FPSelect exploration algorithm.

        This function has to
        - Set the best solution currently found (AttributeSet).
        - Update the set of the attribute sets that satisfy the sensitivity
          threshold (Set[AttributeSet]).
        - Update the list of the explored attributes which is the trace of the
          execution. The information regarding an explored attribute is stored
          as a dictionary with the following key/values:
          * time (float): The time spent since the starting of the exploration
                          in seconds (use timedelta.total_seconds()).
          * attributes (Set[int]): The set of the ids of the attributes.
          * sensitivity (float): The sensitivity of the attribute set.
          * usability_cost (float): The usability cost of the attribute set.
          * cost_explanation (Dict[str: float]): The explanation of the cost of
                                                 the attribute set.
          * state (State): The state of this attribute set (see State class).
        - Log the explored attribute sets for debugging purposes using loguru.

        Note:
            We use the ids of the attributes instead of their name to reduce
            the size of the trace in memory and when saved in json format.
        """
        # While the set S is not empty, we continue the exploration. Note that
        # it is initialized to k empty sets.
        stage = 1
        while self._attr_sets_to_expand:
            logger.debug('---------------------------------------------------')
            logger.debug(f'Starting the stage {stage}.')
            logger.debug(f'The {len(self._attr_sets_to_expand)} attribute sets'
                         f' to expand: {self._attr_sets_to_expand}.')
            logger.debug(f'The {len(self._attr_sets_ignored_supersets)} '
                         'attribute sets which supersets are ignored: '
                         f'{self._attr_sets_ignored_supersets}.')

            # Generate the attribute sets to explore by expanding the set S
            sets_to_explore = self._expand_s()
            logger.debug(f'The {len(sets_to_explore)} attribute sets to '
                         f'explore: {sets_to_explore}.')

            # Hold the next attribute sets to expand sorted by their efficiency
            next_attr_sets_to_expand = SortedDict()

            # For each attribute set to explore  (for C in E)
            for attribute_set in sets_to_explore:
                attr_set_efficiency = self._explore_attribute_set(
                    attribute_set)
                if attr_set_efficiency:  # If its supersets are to explore
                    next_attr_sets_to_expand[attr_set_efficiency] = (
                        attribute_set)

            # Clear the sets to expand to store the ones if there are some
            self._attr_sets_to_expand.clear()

            # After having explored all the attribute sets, get the k most
            # efficient attr. sets that are the next to explore
            for _ in range(min(self._explored_paths,
                               len(next_attr_sets_to_expand))):
                _, most_efficient_attr_set = next_attr_sets_to_expand.popitem(
                    -1)
                self._attr_sets_to_expand.add(most_efficient_attr_set)

            # Next stage
            stage += 1

    def _explore_attribute_set(self, attribute_set: AttributeSet
                               ) -> Optional[float]:
        """Explore an attribute set and return its efficiency if not pruned.

        Args:
            attribute_set: The attribute set to explore.

        Returns:
            The efficiency of the explored attribute set if the supersets of
            this attribute should be explored (i.e., it does not satisfy the
            sensitivity threshold and is not pruned).
        """
        logger.debug(f'Exploring {attribute_set}:')
        efficiency = None  # None returned if its supersets are to be ignored

        # Compute its sensitivity and its cost
        sensitivity = self._sensitivity.evaluate(attribute_set)
        cost, cost_explanation = self._usability_cost.evaluate(attribute_set)
        logger.debug(f'  sensitivity={sensitivity} / usability cost={cost}')

        # If the sensitivity threshold is reached  (s(C) <= alpha)
        if sensitivity <= self._sensitivity_threshold:
            self._satisfying_attribute_sets.add(attribute_set)
            self._attr_sets_ignored_supersets.add(attribute_set)
            attribute_set_state = State.SATISFYING

            # If a minimum cost is found  (c(C) < c_min)
            if cost < self._min_cost:
                self._min_cost = cost
                self._solution = attribute_set
                logger.debug(f'  new solution found: {attribute_set}')
            else:
                logger.debug('  new satisfying attribute set: '
                             f'{attribute_set}')

        # If the sensitivity threshold is not reached but the cost is
        # still below the minimum currently found
        # (s(C) > alpha) && (c(C) < c_min)
        elif cost < self._min_cost:
            # Compute the efficiency of this attribute set
            cost_gain = self._max_cost - cost
            efficiency = cost_gain / sensitivity
            attribute_set_state = State.EXPLORED
            logger.debug('  will explore the supersets of '
                         f'{attribute_set}.')

        # For any other cases (threshold not reached, higher cost) when
        # the pruning methods are used, we ignore their supersets
        elif self._pruning:
            self._attr_sets_ignored_supersets.add(attribute_set)
            attribute_set_state = State.PRUNED
            logger.debug('  will ignore the supersets of: '
                         f'{attribute_set}.')

        # Store this attribute set in the explored sets
        compute_time = str(datetime.now() - self._start_time)
        self._explored_attr_sets.append({
            TraceData.TIME: compute_time,
            TraceData.ATTRIBUTES: attribute_set.attribute_ids,
            TraceData.SENSITIVITY: sensitivity,
            TraceData.USABILITY_COST: cost,
            TraceData.COST_EXPLANATION: cost_explanation,
            TraceData.STATE: attribute_set_state
        })

        # Return the efficiency, or None if its supersets are ignored
        return efficiency

    def _expand_s(self) -> Set[AttributeSet]:
        """Expand the set S to obtain the attribute sets to explore.

        For each S_i of S, we generate the attribute sets to explore that are
        composed of each S_i with one more attribute that is not in S_i.
        E <-- {C = S_i Union {a} :
               For all S_i in S, For all a in A, a Not in S_i}

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
        for set_to_expand in self._attr_sets_to_expand:  # For all S_i in S
            for attribute in self._dataset.candidate_attributes:
                # For all a in A

                # The attr. set C with one more attribute (S_i union {a})
                new_attr_set = deepcopy(set_to_expand)
                new_attr_set.add(attribute)
                # logger.debug(f'Checking the new attribute set '
                #              '{new_attr_set}.')
                add_new_attr_set = True

                # Ignore C if the attr. a is already in the attr. set S_i
                if attribute in set_to_expand:
                    add_new_attr_set = False
                    continue

                # Ignore C if it is a superset of an attr. set of T
                for attr_set_sat in self._satisfying_attribute_sets:
                    if new_attr_set.issuperset(attr_set_sat):
                        add_new_attr_set = False
                        break

                # Ignore C if we use the pruning methods and it is a superset
                # of an attr. set which supersets are to be ignored
                if self._pruning and add_new_attr_set:
                    for attr_set_to_ign in self._attr_sets_ignored_supersets:
                        if new_attr_set.issuperset(attr_set_to_ign):
                            add_new_attr_set = False
                            break

                # If C is fine, it is added to the attr. sets to explore
                if add_new_attr_set:
                    attr_sets_to_explore.add(new_attr_set)
                    # logger.debug(f'Add {new_attr_set} to the sets to '
                    #              ' explore.')

        # Return the set E of the attribute sets to explore, frozen to be
        # usable in a set storage
        return attr_sets_to_explore
