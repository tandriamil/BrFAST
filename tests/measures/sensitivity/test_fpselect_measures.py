#!/usr/bin/python3
"""Test module of the brfast.measures.sensitivity.fpselect module."""

import importlib
import unittest

import pandas as pd
from pandas.testing import assert_frame_equal  # To test DataFrame objects

from brfast.data.attribute import AttributeSet
from brfast.data.dataset import MetadataField
from brfast.measures.sensitivity.fpselect import (
    _get_top_k_fingerprints, TopKFingerprints, PROPORTION_FIELD)

from tests.data import (ATTRIBUTES, DummyCleanDataset, DummyEmptyDataset,
                        DummyFingerprintDataset)

# Import the engine of the analysis module (pandas or modin)
from brfast.config import params


class TestGetTopKFingerprintsFunction(unittest.TestCase):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._attribute_names = [attribute.name for attribute in ATTRIBUTES]

    def test_top_0_fingerprints(self):
        expected_data = dict(
            [(name, list()) for name in self._attribute_names])
        expected_data[PROPORTION_FIELD] = []  # Added during the computation
        # Empty dataframe with columns only
        expected_dataframe = pd.DataFrame(expected_data)
        resulting_dataframe = _get_top_k_fingerprints(
            self._dataset.dataframe, self._attribute_names, 0)
        if params['DataAnalysis']['engine'] == 'modin.pandas':
            resulting_dataframe = resulting_dataframe._to_pandas()

        # Put back the right type as we started from an empty list of values
        for attribute in self._attribute_names:
            source_type = self._dataset.dataframe.dtypes[attribute]
            expected_dataframe[attribute] = expected_dataframe[
                attribute].astype(source_type)

        assert_frame_equal(resulting_dataframe, expected_dataframe,
                           check_frame_type=False)  # As modin can be used

    def test_top_1_fingerprint(self):
        # Rows seem to be sorted : (Chrome, 100, 1) is then first...
        expected_data = {ATTRIBUTES[0].name: ['Chrome'],
                         ATTRIBUTES[1].name: [100],
                         ATTRIBUTES[2].name: [1],
                         PROPORTION_FIELD: [1/5]}
        expected_dataframe = pd.DataFrame(expected_data)
        resulting_dataframe = _get_top_k_fingerprints(
            self._dataset.dataframe, self._attribute_names, 1)
        if params['DataAnalysis']['engine'] == 'modin.pandas':
            resulting_dataframe = resulting_dataframe._to_pandas()
        assert_frame_equal(resulting_dataframe, expected_dataframe,
                           check_frame_type=False)  # As modin can be used

    def test_top_3_fingerprints_non_uniques(self):
        # Rows seem to be sorted : (Chrome, 1) is then before (Edge, 1)
        attribute_names = [attribute.name for attribute in ATTRIBUTES]
        attribute_names.remove(ATTRIBUTES[1].name)
        expected_data = {
            ATTRIBUTES[0].name: ['Chrome', 'Edge', 'Firefox'],
            ATTRIBUTES[2].name: [1, 1, 1],
            PROPORTION_FIELD: [2/5, 2/5, 1/5]
        }
        expected_dataframe = pd.DataFrame(expected_data)
        resulting_dataframe = _get_top_k_fingerprints(
            self._dataset.dataframe, attribute_names, 3)
        if params['DataAnalysis']['engine'] == 'modin.pandas':
            resulting_dataframe = resulting_dataframe._to_pandas()
        assert_frame_equal(resulting_dataframe, expected_dataframe,
                           check_frame_type=False)  # As modin can be used

    def test_top_42_fingerprints_non_uniques(self):
        # Rows seem to be sorted : (Chrome, 1) is then before (Edge, 1)
        attribute_names = [attribute.name for attribute in ATTRIBUTES]
        attribute_names.remove(ATTRIBUTES[1].name)
        expected_data = {
            ATTRIBUTES[0].name: ['Chrome', 'Edge', 'Firefox'],
            ATTRIBUTES[2].name: [1, 1, 1],
            PROPORTION_FIELD: [2/5, 2/5, 1/5]
        }
        expected_dataframe = pd.DataFrame(expected_data)
        resulting_dataframe = _get_top_k_fingerprints(
            self._dataset.dataframe, attribute_names, 42)
        if params['DataAnalysis']['engine'] == 'modin.pandas':
            resulting_dataframe = resulting_dataframe._to_pandas()
        assert_frame_equal(resulting_dataframe, expected_dataframe,
                           check_frame_type=False)  # As modin can be used


class TopKFingerprintsCleanDataset(unittest.TestCase):

    def setUp(self):
        self._dataset = DummyCleanDataset()
        self._attribute_set = AttributeSet(ATTRIBUTES)
        self._candidate_attributes = AttributeSet(ATTRIBUTES)
        self._most_common_fps = 3

    def test_repr(self):
        top_k_fingerprints = TopKFingerprints(self._dataset,
                                              self._most_common_fps)
        self.assertIsInstance(repr(top_k_fingerprints), str)

    def check_top_k_fingerprints(self, expected_nb_browsers: int):
        top_k_fingerprints = TopKFingerprints(self._dataset,
                                              self._most_common_fps)
        result = top_k_fingerprints.evaluate(self._attribute_set)
        self.assertAlmostEqual(result, expected_nb_browsers)

    def test_top_0_fingerprints(self):
        self._most_common_fps = 0
        for attribute in self._candidate_attributes:
            self._attribute_set = AttributeSet([attribute])
            self.check_top_k_fingerprints(0.0)

    def test_top_1_fingerprints(self):
        self._most_common_fps = 1
        top_k_fps_per_attribute = {ATTRIBUTES[0]: 2/5, ATTRIBUTES[1]: 1/5,
                                   ATTRIBUTES[2]: 5/5}
        for attribute in self._candidate_attributes:
            self._attribute_set = AttributeSet([attribute])
            self.check_top_k_fingerprints(top_k_fps_per_attribute[attribute])

    def test_top_2_fingerprints(self):
        self._most_common_fps = 2
        top_k_fps_per_attribute = {ATTRIBUTES[0]: 4/5, ATTRIBUTES[1]: 2/5,
                                   ATTRIBUTES[2]: 5/5}
        for attribute in self._candidate_attributes:
            self._attribute_set = AttributeSet([attribute])
            self.check_top_k_fingerprints(top_k_fps_per_attribute[attribute])

    def test_top_3_fingerprints(self):
        self._most_common_fps = 3
        top_k_fps_per_attribute = {ATTRIBUTES[0]: 5/5, ATTRIBUTES[1]: 3/5,
                                   ATTRIBUTES[2]: 5/5}
        for attribute in self._candidate_attributes:
            self._attribute_set = AttributeSet([attribute])
            self.check_top_k_fingerprints(top_k_fps_per_attribute[attribute])

    def test_top_4_fingerprints(self):
        self._most_common_fps = 4
        top_k_fps_per_attribute = {ATTRIBUTES[0]: 5/5, ATTRIBUTES[1]: 4/5,
                                   ATTRIBUTES[2]: 5/5}
        for attribute in self._candidate_attributes:
            self._attribute_set = AttributeSet([attribute])
            self.check_top_k_fingerprints(top_k_fps_per_attribute[attribute])

    def test_top_5_fingerprints(self):
        self._most_common_fps = 5
        top_k_fps_per_attribute = {ATTRIBUTES[0]: 5/5, ATTRIBUTES[1]: 5/5,
                                   ATTRIBUTES[2]: 5/5}
        for attribute in self._candidate_attributes:
            self._attribute_set = AttributeSet([attribute])
            self.check_top_k_fingerprints(top_k_fps_per_attribute[attribute])

    def test_top_42_fingerprints(self):
        self._most_common_fps = 42
        top_k_fps_per_attribute = {ATTRIBUTES[0]: 5/5, ATTRIBUTES[1]: 5/5,
                                   ATTRIBUTES[2]: 5/5}
        for attribute in self._candidate_attributes:
            self._attribute_set = AttributeSet([attribute])
            self.check_top_k_fingerprints(top_k_fps_per_attribute[attribute])


class TopKFingerprintsUncleanDataset(TopKFingerprintsCleanDataset):

    def setUp(self):
        self._dataset = DummyFingerprintDataset()
        self._attribute_set = AttributeSet(ATTRIBUTES)
        self._candidate_attributes = AttributeSet(ATTRIBUTES)
        self._most_common_fps = 3

    def test_top_1_fingerprints(self):
        self._most_common_fps = 1
        top_k_fps_per_attribute = {ATTRIBUTES[0]: 1/3, ATTRIBUTES[1]: 1/3,
                                   ATTRIBUTES[2]: 3/3}
        for attribute in self._candidate_attributes:
            self._attribute_set = AttributeSet([attribute])
            self.check_top_k_fingerprints(top_k_fps_per_attribute[attribute])

    def test_top_2_fingerprints(self):
        self._most_common_fps = 2
        top_k_fps_per_attribute = {ATTRIBUTES[0]: 2/3, ATTRIBUTES[1]: 2/3,
                                   ATTRIBUTES[2]: 3/3}
        for attribute in self._candidate_attributes:
            self._attribute_set = AttributeSet([attribute])
            self.check_top_k_fingerprints(top_k_fps_per_attribute[attribute])

    def test_top_3_fingerprints(self):
        self._most_common_fps = 3
        top_k_fps_per_attribute = {ATTRIBUTES[0]: 3/3, ATTRIBUTES[1]: 3/3,
                                   ATTRIBUTES[2]: 3/3}
        for attribute in self._candidate_attributes:
            self._attribute_set = AttributeSet([attribute])
            self.check_top_k_fingerprints(top_k_fps_per_attribute[attribute])

    def test_top_4_fingerprints(self):
        self._most_common_fps = 4
        top_k_fps_per_attribute = {ATTRIBUTES[0]: 3/3, ATTRIBUTES[1]: 3/3,
                                   ATTRIBUTES[2]: 3/3}
        for attribute in self._candidate_attributes:
            self._attribute_set = AttributeSet([attribute])
            self.check_top_k_fingerprints(top_k_fps_per_attribute[attribute])

    def test_top_5_fingerprints(self):
        self._most_common_fps = 5
        top_k_fps_per_attribute = {ATTRIBUTES[0]: 3/3, ATTRIBUTES[1]: 3/3,
                                   ATTRIBUTES[2]: 3/3}
        for attribute in self._candidate_attributes:
            self._attribute_set = AttributeSet([attribute])
            self.check_top_k_fingerprints(top_k_fps_per_attribute[attribute])

    def test_top_42_fingerprints(self):
        self._most_common_fps = 42
        top_k_fps_per_attribute = {ATTRIBUTES[0]: 3/3, ATTRIBUTES[1]: 3/3,
                                   ATTRIBUTES[2]: 3/3}
        for attribute in self._candidate_attributes:
            self._attribute_set = AttributeSet([attribute])
            self.check_top_k_fingerprints(top_k_fps_per_attribute[attribute])


if __name__ == '__main__':
    unittest.main()
