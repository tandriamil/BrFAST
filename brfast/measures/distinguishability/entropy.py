#!/usr/bin/python3
"""Module containing the entropy measures of attribute sets."""

from scipy.stats import entropy

from brfast.data import AttributeSet, FingerprintDataset


ENTROPY_BASE = 2


def attribute_set_entropy(fingerprint_dataset: FingerprintDataset,
                          attribute_set: AttributeSet):
    """Compute the entropy of a dataset considering the given attribute set.

    Args:
        fingerprint_dataset: The dataset used to compute the entropy.
        attribute_set: The non-empty attribute set that is considered when
                       computing the entropy of the fingerprints.

    Returns:
        The entropy of the fingerprints considering this attribute set.

    Raises:
        ValueError: The attribute set is empty, no grouping is possible.
        KeyError: An attribute is not in the fingerprint dataset.
    """
    dataframe = fingerprint_dataset.dataframe
    considered_attribute_names = [attribute.name
                                  for attribute in attribute_set]
    distinct_value_count = dataframe.value_counts(considered_attribute_names,
                                                  normalize=True, sort=False)
    return entropy(distinct_value_count, base=ENTROPY_BASE)
