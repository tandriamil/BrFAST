#!/usr/bin/python3
"""Module containing a very basic example."""

from fpselect.algorithm import FPSelect
from fpselect.attribute import Attribute
from fpselect.cost import Cost, CostFunction
from fpselect.sensitivity import SensitivityFunction


def run():
    """Main function to execute the basic example."""
    # Prepare the attributes
    useragent = Attribute(1, 'User-Agent')
    timezone = Attribute(2, 'Time Zone')
    cookies = Attribute(3, 'CookiesEnabled')
    screensize = Attribute(4, 'ScreenSize')
    canvas = Attribute(5, 'Canvas')
    candidate_attributes = {useragent, timezone, cookies, screensize, canvas}

    # Prepare the cost and the sensitivity function
    cost_function = MyCost()
    sensitivity_function = MySensitivity()

    # The two parameters
    sensitivity_threshold = 0.13
    explored_paths = 2

    # The instance of FPSelect
    fpselect_instance = FPSelect(
        candidate_attributes, sensitivity_threshold, explored_paths,
        cost_function, sensitivity_function, save_data=True)

    # Run this instance and get the solution
    fpselect_instance.run()
    print(fpselect_instance.get_solution())


class MySensitivity(SensitivityFunction):
    """My own defined sensitivity function."""

    attributes_weights = {1: 0.01, 2: 0.02, 3: 0.03, 4: 0.02, 5: 0.05}

    def measure(self, attribute_set: set) -> float:
        """Measures the sensitivity of an attribute set.

        Args:
            attribute_set: The attribute set whose sensitivity is to be
              measured.

        Returns:
            The sensitivity considering this attribute set.
        """
        sensitivity = 0
        for attribute in attribute_set:
            sensitivity += self.attributes_weights[attribute.get_id()]
        return sensitivity


class MyCost(CostFunction):
    """My own defined cost function."""

    attributes_costs = {1: 0.03, 2: 0.05, 3: 0.04, 4: 0.08, 5: 0.01}

    def measure(self, attribute_set: set[Attribute]) -> float:
        """Measures the cost of an attribute set.

        Args
        attribute_set: The set of attributes whose cost is to be measured.

        Returns:
            A Cost object containing the value and description of the cost.
        """
        value, description = 0, ''
        for attribute in attribute_set:
            value += self.attributes_costs[attribute.get_id()]
            description += str(self.attributes_costs[attribute.get_id()]) + ' '

        return Cost(value, description)


if __name__ == '__main__':
    run()
