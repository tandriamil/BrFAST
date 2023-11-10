#!/usr/bin/python3
"""A dummy exploration using the example of our FPSelect paper."""

import importlib

from brfast.data.attribute import Attribute, AttributeSet
from brfast.data.dataset import FingerprintDataset, MetadataField
from brfast.exploration.conditional_entropy import ConditionalEntropy
from brfast.exploration.entropy import Entropy
from brfast.exploration.fpselect import FPSelect
from brfast.measures import UsabilityCostMeasure, SensitivityMeasure

# Import the engine of the analysis module (pandas or modin)
from brfast.config import params
pd = importlib.import_module(params['DataAnalysis']['engine'])


# The parameters of the three exploration methods that are tested
SENSITIVITY_THRESHOLD = 0.15  # The threshold of the FPSelect paper example
EXPLORED_PATHS = 2  # Specific to FPSelect
PRUNING_ON = True  # Specific to FPSelect


def main():
    """Execute the three exploration methods on the dummy FPSelect example."""
    sensitivity_measure = DummySensitivityMeasure()
    usability_cost_measure = DummyUsabilityCostMeasure()
    dataset = DummyFingerprintDataset()

    # Entropy baseline
    entropy_exploration = Entropy(sensitivity_measure, usability_cost_measure,
                                  dataset, SENSITIVITY_THRESHOLD)
    print('Beginning of the entropy execution...')
    entropy_exploration.run()
    entropy_solution = entropy_exploration.get_solution()
    entropy_explored_attribute_sets = len(
        entropy_exploration.get_explored_attribute_sets())
    print(f'The solution found by the entropy baseline is {entropy_solution} '
          f'after exploring {entropy_explored_attribute_sets} attribute sets.')

    # Conditional entropy baseline
    cond_ent_exploration = ConditionalEntropy(
        sensitivity_measure, usability_cost_measure, dataset,
        SENSITIVITY_THRESHOLD)
    print('Beginning of the conditional entropy execution...')
    cond_ent_exploration.run()
    cond_ent_solution = cond_ent_exploration.get_solution()
    cond_ent_explored_attribute_sets = len(
        cond_ent_exploration.get_explored_attribute_sets())
    print('The solution found by the conditional entropy baseline is '
          f'{cond_ent_solution} after exploring '
          f'{cond_ent_explored_attribute_sets} attribute sets.')

    # FPSelect method
    fpselect_exploration = FPSelect(
        sensitivity_measure, usability_cost_measure, dataset,
        SENSITIVITY_THRESHOLD, EXPLORED_PATHS, PRUNING_ON)
    print('Beginning of the FPSelect execution...')
    fpselect_exploration.run()
    fpselect_solution = fpselect_exploration.get_solution()
    fpselect_explored_attribute_sets = len(
        fpselect_exploration.get_explored_attribute_sets())
    print(f'The solution found by FPSelect is {fpselect_solution} after '
          f'exploring {fpselect_explored_attribute_sets} attribute sets.')


# ----- Definition of the dummy sensitivity and usability cost measure
class DummySensitivityMeasure(SensitivityMeasure):
    """A dummy sensitivity measure that returns hard-coded values.

    These values come from the example of our FPSelect paper.
    """

    sensitivities = {
        frozenset({}): 1.0,
        frozenset({1}): 0.3, frozenset({2}): 0.3, frozenset({3}): 0.25,
        frozenset({1, 2}): 0.15, frozenset({1, 3}): 0.25,
        frozenset({2, 3}): 0.20,
        frozenset({1, 2, 3}): 0.05
    }

    def evaluate(self, attribute_set: AttributeSet) -> float:
        """Measure the sensitivity of an attribute set.

        The sensitivity measure is required to be monotonously decreasing as we
        add attributes (see the FPSelect paper).

        Args
            attribute_set: The attribute set which sensitivity is to be
                           measured.

        Returns:
            The sensitivity of the attribute set.
        """
        return self.sensitivities[frozenset(attribute_set.attribute_ids)]


class DummyUsabilityCostMeasure(UsabilityCostMeasure):
    """A dummy usability cost measure that returns hard-coded values.

    These values come from the example of our FPSelect paper.
    """

    usability_costs = {
        frozenset({}): 0,
        frozenset({1}): 10, frozenset({2}): 15, frozenset({3}): 15,
        frozenset({1, 2}): 20, frozenset({1, 3}): 17,
        frozenset({2, 3}): 25,
        frozenset({1, 2, 3}): 30
    }

    def evaluate(self, attribute_set: AttributeSet) -> tuple[int,
                                                             dict[str, int]]:
        """Measure the usability cost of an attribute set.

        The usability cost measure is required to be strictly increasing as we
        add attributes (see the FPSelect paper).

        Args
            attribute_set: The attribute set which cost is to be measured.

        Returns:
            A pair with the cost and its explanation. The cost is a numerical
            value whereas the explanation is a dictionary associating a cost
            dimension (str) to a cost value (float).
        """
        attribute_cost = self.usability_costs[
            frozenset(attribute_set.attribute_ids)]
        return attribute_cost, {'total_cost': attribute_cost}


# ----- Definition of the dummy dataset
class DummyFingerprintDataset(FingerprintDataset):
    """Dummy fingerprint class to define the required functions."""

    attributes = [Attribute(1, 'user_agent'), Attribute(2, 'timezone'),
                  Attribute(3, 'do_not_track')]

    def _set_candidate_attributes(self):
        """Set the candidate attributes.

        The default behavior is to generate the candidate attributes from the
        columns of the DataFrame, ignoring the browser_id and time_of_collect
        fields.
        """
        self._candidate_attributes = AttributeSet(self.attributes)

    def _process_dataset(self):
        """Process the dataset to obtain a pandas DataFrame from the file.

        - The resulting fingerprint dataset is stored in self._dataframe.
        - The fingerprint dataset has to be a pandas DataFrame with the two
          indices being  browser_id (int64) and time_of_collect (datetime64).
        - The columns are named after the attributes and have the value
          collected for the browser browser_id at the time time_of_collect.
        - The name of each column should correspond to the attribute.name
          property of an attribute of the candidate attributes.

        The default behavior is to generate a DataFrame from the csv stored at
        self._dataset_path with the two indices set.
        """
        self._datas = {
            MetadataField.BROWSER_ID: [1, 2, 3, 2, 3],
            MetadataField.TIME_OF_COLLECT: pd.date_range('2021-03-12',
                                                         periods=5, freq='H'),
            self.attributes[0].name: ['Firefox', 'Chrome', 'Edge', 'Chrome',
                                      'Edge'],
            self.attributes[1].name: [60, 120, 90, 120, 90],
            self.attributes[2].name: [1, 1, 1, 1, 1]
        }
        self._dataframe = pd.DataFrame(self._datas)
        self._dataframe.set_index(
            [MetadataField.BROWSER_ID, MetadataField.TIME_OF_COLLECT],
            inplace=True)


if __name__ == '__main__':
    main()
