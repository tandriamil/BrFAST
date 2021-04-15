#!/usr/bin/python3
"""Test module of the data module of BrFAST."""

import importlib
import unittest
from os import path
from pathlib import PurePath

from brfast.data import (
    Attribute, AttributeSet, FingerprintDatasetFromCSVFile, MetadataField,
    MissingMetadatasFields)

from tests.data import (
    ATTRIBUTES, DummyFingerprintDataset, DummyDatasetMissingBrowserId,
    DummyDatasetMissingTimeOfCollect)

# Import the engine of the analysis module (pandas or modin)
from brfast import config
pd = importlib.import_module(config['DataAnalysis']['engine'])

RELATIVE_PATH_TO_FP_SAMPLE = 'assets/fingerprint-sample.csv'


class TestAttribute(unittest.TestCase):

    def setUp(self):
        self._attr_id, self._name = 1, 'user_agent'
        self.attribute = Attribute(self._attr_id, self._name)

    def test_init(self):
        self.assertEqual(self.attribute.attr_id, self._attr_id)
        self.assertEqual(self.attribute.name, self._name)

    def test_repr(self):
        self.assertIsInstance(f'{self.attribute}', str)

    def test_read_only_properties(self):
        with self.assertRaises(AttributeError):
            self.attribute.attr_id = 5
        with self.assertRaises(AttributeError):
            self.attribute.name = 'screen_width'

    def test_equality_new_attribute_same_id_name(self):
        # Another attribute object with the same id / name
        new_attribute = Attribute(self._attr_id, self._name)
        self.assertEqual(new_attribute, self.attribute)
        self.assertTrue(self.attribute == new_attribute)
        self.assertFalse(self.attribute != new_attribute)

    def test_equality_new_attribute_different_id_name(self):
        # Another attribute object with a different id and name
        other_attribute = Attribute(42, 'unknown')
        self.assertNotEqual(other_attribute, self.attribute)
        self.assertFalse(self.attribute == other_attribute)
        self.assertTrue(self.attribute != other_attribute)

    def test_inequality_with_integers(self):
        self.assertNotEqual(self._attr_id, self.attribute)


class TestAttributeSet(unittest.TestCase):

    def setUp(self):
        self._user_agent = ATTRIBUTES[0]
        self._timezone = ATTRIBUTES[1]
        self._empty_attr_set = AttributeSet()
        self._attribute_set = AttributeSet({self._user_agent, self._timezone})

    def test_len(self):
        self.assertEqual(0, len(self._empty_attr_set))
        self.assertEqual(2, len(self._attribute_set))

    def test_attributes(self):
        attributes = [attribute for attribute in self._attribute_set]
        self.assertEqual(
            Attribute(self._user_agent.attr_id, self._user_agent.name),
            attributes[0])
        self.assertEqual(
            Attribute(self._timezone.attr_id, self._timezone.name),
            attributes[1])
        self.assertEqual(2, len(attributes))

    def test_attribute_names(self):
        attribute_names = self._attribute_set.attribute_names
        self.assertEqual([self._user_agent.name, self._timezone.name],
                         attribute_names)

    def test_attribute_ids(self):
        attribute_ids = self._attribute_set.attribute_ids
        self.assertEqual([self._user_agent.attr_id, self._timezone.attr_id],
                         attribute_ids)

    def test_add_new_attribute(self):
        new_attr_set = AttributeSet({self._user_agent})
        self.assertEqual(1, len(new_attr_set))
        new_attribute = ATTRIBUTES[2]
        new_attr_set.add(new_attribute)
        self.assertEqual(2, len(new_attr_set))
        self.assertIn(new_attribute, new_attr_set)

    def test_add_new_attribute_already_present(self):
        new_attr_set = AttributeSet({self._user_agent, self._timezone})
        self.assertEqual(2, len(new_attr_set))
        new_attr_set.add(self._timezone)
        self.assertEqual(2, len(new_attr_set))

    def test_remove(self):
        new_attr_set = AttributeSet({self._user_agent, self._timezone})
        self.assertEqual(2, len(new_attr_set))
        new_attr_set.remove(self._user_agent)
        self.assertEqual(1, len(new_attr_set))
        self.assertNotIn(self._user_agent, new_attr_set)

    def test_remove_attribute_not_present(self):
        new_attr_set = AttributeSet({self._user_agent, self._timezone})
        self.assertEqual(2, len(new_attr_set))
        non_present_attribute = Attribute(42, 'unknown')
        with self.assertRaises(KeyError):
            new_attr_set.remove(non_present_attribute)
        self.assertEqual(2, len(new_attr_set))

    def test_is_superset(self):
        set_single_attr = AttributeSet({self._user_agent})
        self.assertTrue(self._attribute_set.issuperset(set_single_attr))
        self.assertFalse(set_single_attr.issuperset(self._attribute_set))

    def test_is_superset_different_set(self):
        set_another_attr = AttributeSet({Attribute(42, 'unknown'),
                                         self._user_agent})
        self.assertFalse(set_another_attr.issuperset(self._attribute_set))
        self.assertFalse(self._attribute_set.issuperset(set_another_attr))

    def test_is_subset(self):
        set_single_attr = AttributeSet({self._user_agent})
        self.assertFalse(self._attribute_set.issubset(set_single_attr))
        self.assertTrue(set_single_attr.issubset(self._attribute_set))

    def test_is_subset_different_set(self):
        set_another_attr = AttributeSet({Attribute(42, 'unknown'),
                                         self._user_agent})
        self.assertFalse(set_another_attr.issubset(self._attribute_set))
        self.assertFalse(self._attribute_set.issubset(set_another_attr))

    def test_get_attribute_by_id(self):
        self.assertEqual(
            self._user_agent,
            self._attribute_set.get_attribute_by_id(self._user_agent.attr_id))
        self.assertEqual(
            self._timezone,
            self._attribute_set.get_attribute_by_id(self._timezone.attr_id))
        with self.assertRaises(KeyError):
            self._attribute_set.get_attribute_by_id(-1)

    def test_get_attribute_by_name(self):
        self.assertEqual(
            self._user_agent,
            self._attribute_set.get_attribute_by_name(self._user_agent.name))
        self.assertEqual(
            self._timezone,
            self._attribute_set.get_attribute_by_name(self._timezone.name))
        with self.assertRaises(KeyError):
            self._attribute_set.get_attribute_by_name('unknown')


class TestFingerprintDatasetFromCSVFile(unittest.TestCase):

    def setUp(self):
        tests_module_path = PurePath(path.abspath(__file__)).parents[1]
        self._fingerprint_sample_path = tests_module_path.joinpath(
            RELATIVE_PATH_TO_FP_SAMPLE)

    def test_fingerprint_sample(self):
        sample_dataset = FingerprintDatasetFromCSVFile(
            self._fingerprint_sample_path)
        self.assertIsInstance(sample_dataset.dataframe, pd.DataFrame)
        self.assertEqual(len(sample_dataset.dataframe), 1)
        self.assertEqual(sample_dataset.candidate_attributes,
                         AttributeSet(ATTRIBUTES))

    def test_missing_metadatas(self):
        with self.assertRaises(MissingMetadatasFields):
            DummyDatasetMissingBrowserId()
        with self.assertRaises(MissingMetadatasFields):
            DummyDatasetMissingTimeOfCollect()

    def test_dataset_property(self):
        dummy_fp_dataset = DummyFingerprintDataset()
        self.assertIsInstance(dummy_fp_dataset.dataframe, pd.DataFrame)
        self.assertEqual(
            len(dummy_fp_dataset.dataframe),
            len(dummy_fp_dataset._datas[MetadataField.BROWSER_ID]))
        with self.assertRaises(AttributeError):
            dummy_fp_dataset.dataframe = pd.DataFrame()

    def test_dataset_path_property(self):
        sample_dataset = FingerprintDatasetFromCSVFile(
            self._fingerprint_sample_path)
        self.assertEqual(sample_dataset.dataset_path,
                         self._fingerprint_sample_path)

    def test_candidate_attributes_property(self):
        dummy_fp_dataset = DummyFingerprintDataset()
        self.assertEqual(dummy_fp_dataset.candidate_attributes,
                         AttributeSet(ATTRIBUTES))
        with self.assertRaises(AttributeError):
            dummy_fp_dataset.candidate_attributes = AttributeSet()


if __name__ == '__main__':
    unittest.main()
