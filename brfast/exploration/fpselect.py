#!/usr/bin/python3
"""Module containing the FPSelect exploration algorithm."""

from datetime import datetime
from math import ceil
from multiprocessing import Pool
from multiprocessing.managers import ListProxy
from os import cpu_count
from typing import Any, Dict, List, Set, Tuple

from loguru import logger

from brfast.config import params
from brfast.data.attribute import AttributeSet
from brfast.data.dataset import FingerprintDataset
from brfast.exploration import (Exploration, ExplorationParameters, State,
                                TraceData)
from brfast.measures import SensitivityMeasure, UsabilityCostMeasure


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
            raise AttributeError('The number of explored paths is required to '
                                 'be a positive number.')

        # Initialize the specific parameters of FPSelect
        self._explored_paths = explored_paths
        self._pruning = pruning
        logger.info(f'Initialized FPSelect with {explored_paths} paths to '
                    'explore.')
        if pruning:
            logger.info('Pruning methods are activated.')
        else:
            logger.info('Pruning methods are ignored.')

        # Initialize the minimum cost currently found
        self._solution.append(float('inf'))  # Stored in self._solution[1]

        # The set S of the attributes set to expand at each step, initialized
        # to k empty sets
        self._attribute_sets_to_expand = set({AttributeSet()})

        # The set I of the attribute sets which supersets are to ignore
        self._attribute_sets_ignored_supersets = set()

    @property
    def parameters(self) -> Dict[str, Any]:
        """Give the parameters of the exploration as a dictionary.

        Returns:
            The parameters as a dictionary of their name and their value.
        """
        parameters = self._default_parameters()
        parameters.update({
            FPSelectParameters.EXPLORED_PATHS: self._explored_paths,
            FPSelectParameters.PRUNING: self._pruning
        })
        return parameters

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
        while self._attribute_sets_to_expand:
            logger.debug('---------------------------------------------------')
            logger.debug(f'Starting the stage {stage}.')
            logger.debug(f'The {len(self._attribute_sets_to_expand)} attribute'
                         f' sets to expand: {self._attribute_sets_to_expand}.')
            logger.debug(f'The {len(self._attribute_sets_ignored_supersets)} '
                         'attribute sets which supersets are ignored: '
                         f'{self._attribute_sets_ignored_supersets}.')

            # Generate the attribute sets to explore by expanding the set S
            sets_to_explore = self._expand_s()
            logger.debug(f'The {len(sets_to_explore)} attribute sets to '
                         f'explore: {sets_to_explore}.')

            # Explore the level and retrieve the next attribute sets to expand
            # sorted by their efficiency (the most efficient are firsts)
            next_attr_sets_to_expand = self._explore_level(sets_to_explore)
            logger.debug(f'After exploring the level {stage}, we obtain '
                         f'{len(next_attr_sets_to_expand)} attribute sets to '
                         'expand.')

            # Clear the sets to expand to store the ones if there are some
            self._attribute_sets_to_expand.clear()

            # After having explored all the attribute sets, get the k most
            # efficient attr. sets that are the next to explore
            for best_atset in sorted(next_attr_sets_to_expand,
                                     key=next_attr_sets_to_expand.get,
                                     reverse=True)[:self._explored_paths]:
                self._attribute_sets_to_expand.add(best_atset)

            # Next stage
            stage += 1

    def _explore_level(self, attribute_sets_to_explore: Set[AttributeSet]
                       ) -> Dict[AttributeSet, float]:
        """Explore the attribute sets of a level (i.e., having the same size).

        Args:
            attribute_sets_to_explore: The attribute sets of this level to
                                       explore.

        Returns:
            The resulting attribute sets that can be explored with their
            efficiency. Only a subset of these will actually be explored.
        """
        # Dictionary of { AttributeSet => efficiency } to build the list of the
        # next attribute sets to explore that will be sorted at the end
        attribute_sets_efficiency = {}

        def update_after_exploration(result: Tuple[Dict[AttributeSet, float],
                                                   Set[AttributeSet],
                                                   Set[AttributeSet]]):
            """Update the informations after exploring a level.

            Args:
                result: A triplet with
                    - The attribute sets that could be explored afterwards and
                       their efficiency.
                    - The attribute sets that satisfy the threshold.
                    - The attribute sets which supersets are to be ignored.

            Note: This is executed by the main thread and does not pose any
                  concurrency or synchronization problem.
            """
            attr_sets_eff, satisf_attr_sets, attr_sets_ign_sups = result
            attribute_sets_efficiency.update(attr_sets_eff)
            self._attribute_sets_ignored_supersets.update(attr_sets_ign_sups)
            self._satisfying_attribute_sets.extend(satisf_attr_sets)

        # If we execute on a single process
        if not params.getboolean('Multiprocessing', 'explorations'):
            logger.debug('Exploring the attribute sets of this level on a '
                         'single process...')
            update_after_exploration(
                _explore_attribute_sets(
                    attribute_sets_to_explore, self._sensitivity,
                    self._usability_cost, self._sensitivity_threshold,
                    self._max_cost, self._solution, self._explored_attr_sets,
                    self._start_time, self._pruning))
            return attribute_sets_efficiency

        # Infer the number of cores to use
        free_cores = params.getint('Multiprocessing', 'free_cores')
        nb_cores = max(cpu_count() - free_cores, 1)
        attribute_sets_per_core = int(ceil(len(attribute_sets_to_explore)
                                           / nb_cores))
        logger.debug(f'Sharing {len(attribute_sets_to_explore)} attribute sets'
                     f' to explore over {nb_cores}(+{free_cores}) cores, hence'
                     f' {attribute_sets_per_core} attribute sets per core.')

        # Spawn a number of processes equal to the number of cores
        attribute_sets_to_explore_list = list(attribute_sets_to_explore)
        async_results = []
        with Pool(processes=nb_cores) as pool:
            for process_id in range(nb_cores):

                # Generate the attribute sets to explore for this process
                start_id = process_id * attribute_sets_per_core
                end_id = (process_id + 1) * attribute_sets_per_core
                subset_attr_sets_to_explore = (
                    attribute_sets_to_explore_list[start_id:end_id])

                async_result = pool.apply_async(
                    _explore_attribute_sets,
                    args=(subset_attr_sets_to_explore, self._sensitivity,
                          self._usability_cost, self._sensitivity_threshold,
                          self._max_cost, self._solution,
                          self._explored_attr_sets, self._start_time,
                          self._pruning),
                    callback=update_after_exploration)
                async_results.append(async_result)

            # Wait for all the processes to finish (otherwise we would exit
            # before collecting their result)
            for async_result in async_results:
                async_result.wait()

        return attribute_sets_efficiency

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
        # The set E of the next attribute sets to explore
        next_attr_sets_to_explore = set()

        # If we execute on a single process
        if not params.getboolean('Multiprocessing', 'explorations'):
            logger.debug('Expanding the next attribute sets to explore on a '
                         'single process...')
            return _expand_attribute_sets(
                self._attribute_sets_to_expand,
                self._dataset.candidate_attributes,
                self.get_satisfying_attribute_sets(),
                self._attribute_sets_ignored_supersets, self._pruning)

        # Infer the number of cores to use
        free_cores = params.getint('Multiprocessing', 'free_cores')
        nb_cores = max(cpu_count() - free_cores, 1)
        attribute_sets_per_core = int(ceil(len(self._attribute_sets_to_expand)
                                           / nb_cores))
        logger.debug(f'Sharing {len(self._attribute_sets_to_expand)} attribute'
                     f' sets to expand over {nb_cores}(+{free_cores}) cores, '
                     f'hence {attribute_sets_per_core} attribute sets per '
                     'core.')

        def update_next_attribute_sets_to_explore(result: Set[AttributeSet]):
            """Update the complete set of the next attribute sets to explore.

            Args:
                result: The next attribute sets to explore given by a process.

            Note: This is executed by the main thread and does not pose any
                  concurrency or synchronization problem.
            """
            next_attr_sets_to_explore.update(result)

        # Spawn a number of processes equal to the number of cores
        satisfying_attribute_sets = self.get_satisfying_attribute_sets()
        attribute_sets_to_expand_as_list = list(self._attribute_sets_to_expand)
        async_results = []
        with Pool(processes=nb_cores) as pool:
            for process_id in range(nb_cores):
                # Generate the attribute sets to expand for this process
                start_id = process_id * attribute_sets_per_core
                end_id = (process_id + 1) * attribute_sets_per_core
                process_attr_sets_to_expand = (
                    attribute_sets_to_expand_as_list[start_id:end_id])

                async_result = pool.apply_async(
                    _expand_attribute_sets,
                    args=(process_attr_sets_to_expand,
                          self._dataset.candidate_attributes,
                          satisfying_attribute_sets,
                          self._attribute_sets_ignored_supersets,
                          self._pruning),
                    callback=update_next_attribute_sets_to_explore)
                async_results.append(async_result)

            # Wait for all the processes to finish (otherwise we would exit
            # before collecting their result)
            for async_result in async_results:
                async_result.wait()

        return next_attr_sets_to_explore


def _explore_attribute_sets(attribute_sets_to_explore: List[AttributeSet],
                            sensitivity_measure: SensitivityMeasure,
                            usability_cost_measure: UsabilityCostMeasure,
                            sensitivity_threshold: float, max_cost: float,
                            solution_storage: ListProxy,
                            explored_attribute_sets: ListProxy,
                            start_time: datetime, use_pruning_methods: bool
                            ) -> Tuple[Dict[AttributeSet, float],
                                       Set[AttributeSet],
                                       Set[AttributeSet]]:
    """Explore the attribute sets of a given level.

    Args:
        attribute_sets_to_explore: The attribute sets to explore of this level.
                                   Note that they all have the same size.
        sensitivity_measure: The sensitivity measure to use.
        usability_cost_measure: The usability cost measure to use.
        sensitivity_threshold: The sensitivity threshold.
        max_cost: The maximum cost when using all the candidate attributes.
        solution_storage: The storage of the solution as a list. The first
                          element is the best attribute set and the second is
                          the current minimum cost.
        explored_attribute_sets: The storage of the explored attribute sets.
        start_time: The start time of the exploration.
        use_pruning_methods: Whether we use pruning methods or not.

    Returns:
        A triplet with
        - The attribute sets that could be explored afterwards and their
          efficiency.
        - The attribute sets that satisfy the sensitivity threshold.
        - The attribute sets which supersets are to be ignored.
    """
    process_attribute_sets_efficiency = {}
    process_satisfying_attribute_sets = set()
    process_attribute_sets_ignored_supersets = set()

    for attribute_set in attribute_sets_to_explore:
        logger.debug(f'Exploring {attribute_set}:')
        attribute_set_state = State.EXPLORED

        # Compute its sensitivity and its cost
        sensitivity = sensitivity_measure.evaluate(attribute_set)
        cost, cost_explanation = usability_cost_measure.evaluate(attribute_set)
        logger.debug(f'  sensitivity={sensitivity} / usability cost={cost}')

        # Get the current minimum cost. Note that it can be updated afterwards,
        # but it does not change the overall result. The only effect is that
        # few additional attribute sets can be put in the
        # process_attribute_sets_efficiency storage.
        current_min_cost = solution_storage[1]

        # If the sensitivity threshold is reached  (s(C) <= alpha)
        if sensitivity <= sensitivity_threshold:
            process_satisfying_attribute_sets.add(attribute_set)
            process_attribute_sets_ignored_supersets.add(attribute_set)
            attribute_set_state = State.SATISFYING

            # If a minimum cost is found  (c(C) < c_min)
            if cost < current_min_cost:
                solution_storage[1] = cost
                solution_storage[0] = attribute_set
                logger.debug(f'  new solution found: {attribute_set}')
            else:
                logger.debug('  new satisfying attribute set: '
                             f'{attribute_set}')

        # If the sensitivity threshold is not reached but the cost is
        # still below the minimum currently found
        # (s(C) > alpha) && (c(C) < c_min)
        elif cost < current_min_cost:
            # Compute the efficiency of this attribute set
            cost_gain = max_cost - cost
            efficiency = cost_gain / sensitivity
            attribute_set_state = State.EXPLORED

            # Add this attribute sets to those to explore
            process_attribute_sets_efficiency[attribute_set] = efficiency
            logger.debug(f'  will explore the supersets of {attribute_set}.')

        # For any other cases (threshold not reached, higher cost) when
        # the pruning methods are used, we ignore their supersets
        elif use_pruning_methods:
            process_attribute_sets_ignored_supersets.add(attribute_set)
            attribute_set_state = State.PRUNED
            logger.debug(f'  will ignore the supersets of {attribute_set}.')

        # Store this attribute set in the explored sets
        compute_time = str(datetime.now() - start_time)
        explored_attribute_sets.append({
            TraceData.TIME: compute_time,
            TraceData.ATTRIBUTES: attribute_set.attribute_ids,
            TraceData.SENSITIVITY: sensitivity,
            TraceData.USABILITY_COST: cost,
            TraceData.COST_EXPLANATION: cost_explanation,
            TraceData.STATE: attribute_set_state
        })

    return (process_attribute_sets_efficiency,
            process_satisfying_attribute_sets,
            process_attribute_sets_ignored_supersets)


def _expand_attribute_sets(attr_sets_to_expand: List[AttributeSet],
                           candidate_attributes: AttributeSet,
                           satisfying_attribute_sets: Set[AttributeSet],
                           attribute_sets_ignored_supersets: Set[AttributeSet],
                           use_pruning_methods: bool) -> Set[AttributeSet]:
    """Expand a subset of the attribute sets to expand.

    Args:
        attr_sets_to_expand: The attribute sets to expand.
        candidate_attributes: The complete set of the candidate attributes.
        satisfying_attribute_sets: The attribute sets that satisfy the
                                   sensitivity threshold.
        attribute_sets_ignored_supersets: The attribute sets for which to
                                          ignore their supersets.
        use_pruning_methods: Whether we use the pruning methods or not.

    Returns:
        The set of the next attribute sets to explore.
    """
    next_attr_sets_to_explore = set()

    # Generate the attr. sets composed of S_i with one more attr.
    # For all S_i in S
    for set_to_expand in attr_sets_to_expand:
        # For all a in A diff C
        for attribute in candidate_attributes:
            if attribute in set_to_expand:
                continue

            # The attr. set C with one more attribute (S_i union {a})
            new_attr_set = AttributeSet(set_to_expand)
            new_attr_set.add(attribute)
            add_new_attr_set = True

            # Ignore C if the attr. a is already in the attr. set S_i
            if attribute in set_to_expand:
                add_new_attr_set = False
                continue

            # Ignore C if it is a superset of an attr. set of T
            for attr_set_sat in satisfying_attribute_sets:
                if new_attr_set.issuperset(attr_set_sat):
                    add_new_attr_set = False
                    break

            # Ignore C if we use the pruning methods and it is a superset
            # of an attr. set which supersets are to be ignored
            if use_pruning_methods and add_new_attr_set:
                for attr_set_to_ign in attribute_sets_ignored_supersets:
                    if new_attr_set.issuperset(attr_set_to_ign):
                        add_new_attr_set = False
                        break

            # If C is fine, it is added to the attr. sets to explore
            if add_new_attr_set:
                next_attr_sets_to_explore.add(new_attr_set)

    return next_attr_sets_to_explore


# ============================== Utility Classes ==============================
class FPSelectParameters(ExplorationParameters):
    """Class representing the parameters of the FPSelect exploration alg."""

    EXPLORED_PATHS = 'explored_paths'
    PRUNING = 'pruning'
# =========================== End of Utility Classes ==========================
