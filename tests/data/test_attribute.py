#!/usr/bin/python3
"""Test module of the data module of BrFAST."""

import unittest

from brfast.data.attribute import Attribute, AttributeSet, DuplicateAttributeId

from tests.data import ATTRIBUTES


class TestAttribute(unittest.TestCase):

    def setUp(self):
        self._attribute_id, self._name = 5, 'user_agent'
        self._attribute = Attribute(self._attribute_id, self._name)

    def test_init(self):
        self.assertEqual(self._attribute.attribute_id, self._attribute_id)
        self.assertEqual(self._attribute.name, self._name)

    def test_repr(self):
        self.assertIsInstance(f'{self._attribute}', str)

    def test_read_only_properties(self):
        with self.assertRaises(AttributeError):
            self._attribute.attribute_id = 7
        with self.assertRaises(AttributeError):
            self._attribute.name = 'screen_width'

    def test_equality_new_attribute_same_id_name(self):
        # Another attribute object with the same id / name
        new_attribute = Attribute(self._attribute_id, self._name)
        self.assertEqual(new_attribute, self._attribute)
        self.assertTrue(self._attribute == new_attribute)
        self.assertFalse(self._attribute != new_attribute)

    def test_equality_new_attribute_different_id_name(self):
        # Another attribute object with a different id and name
        other_attribute = Attribute(42, 'unknown')
        self.assertNotEqual(other_attribute, self._attribute)
        self.assertFalse(self._attribute == other_attribute)
        self.assertTrue(self._attribute != other_attribute)

    def test_inequality(self):
        lower_id_attribute = Attribute(1, 'higher_id_attribute')
        higher_id_attribute = Attribute(42, 'higher_id_attribute')
        self.assertTrue(self._attribute > lower_id_attribute)
        self.assertFalse(self._attribute < lower_id_attribute)
        self.assertTrue(higher_id_attribute > self._attribute)
        self.assertFalse(higher_id_attribute < self._attribute)

    def test_inequality_with_integers(self):
        lower_id, higher_id = 1, 42
        with self.assertRaises(TypeError):
            self._attribute > lower_id
        with self.assertRaises(TypeError):
            self._attribute < lower_id
        with self.assertRaises(TypeError):
            higher_id > self._attribute
        with self.assertRaises(TypeError):
            higher_id < self._attribute

    def test_difference_with_integers(self):
        self.assertNotEqual(self._attribute_id, self._attribute)


class TestAttributeSet(unittest.TestCase):

    def setUp(self):
        self._user_agent = ATTRIBUTES[0]
        self._timezone = ATTRIBUTES[1]
        self._do_not_track = ATTRIBUTES[2]
        self._empty_attr_set = AttributeSet()
        self._single_attribute_set = AttributeSet({self._timezone})
        self._attribute_set = AttributeSet({self._user_agent, self._timezone,
                                            self._do_not_track})

    def test_create_attribute_set_duplicated_id(self):
        duplicated_id_attribute = Attribute(
            self._timezone.attribute_id, 'duplicated_id_attribute')
        with self.assertRaises(DuplicateAttributeId):
            wrong_attribute_set = AttributeSet(
                [self._user_agent, duplicated_id_attribute, self._timezone])
            # NOTE We used a list here as using a set would lead to the
            #      duplicated attributes having the same hash as it relies only
            #      on the id of the attribute.

    def test_repr(self):
        self.assertIsInstance(repr(self._empty_attr_set), str)
        self.assertIsInstance(repr(self._single_attribute_set), str)
        self.assertIsInstance(repr(self._attribute_set), str)

    def test_len(self):
        self.assertEqual(0, len(self._empty_attr_set))
        self.assertEqual(1, len(self._single_attribute_set))
        self.assertEqual(3, len(self._attribute_set))

    def test_iter(self):
        empty_attributes = [attribute for attribute in self._empty_attr_set]
        self.assertEqual(0, len(empty_attributes))

        single_attributes = [attribute
                             for attribute in self._single_attribute_set]
        self.assertEqual(1, len(single_attributes))
        self.assertEqual(self._timezone, single_attributes[0])

        attributes = [attribute for attribute in self._attribute_set]
        self.assertEqual(3, len(attributes))
        self.assertEqual(self._user_agent, attributes[0])
        self.assertEqual(self._timezone, attributes[1])
        self.assertEqual(self._do_not_track, attributes[2])

    def test_attribute_names(self):
        empty_attribute_names = self._empty_attr_set.attribute_names
        self.assertEqual(0, len(empty_attribute_names))

        single_attribute_names = self._single_attribute_set.attribute_names
        self.assertEqual(1, len(single_attribute_names))
        self.assertEqual(self._timezone.name, single_attribute_names[0])

        attribute_names = self._attribute_set.attribute_names
        self.assertEqual(3, len(attribute_names))
        self.assertEqual([self._user_agent.name, self._timezone.name,
                          self._do_not_track.name],
                         attribute_names)

    def test_attribute_ids(self):
        empty_attribute_ids = self._empty_attr_set.attribute_ids
        self.assertEqual(0, len(empty_attribute_ids))

        single_attribute_ids = self._single_attribute_set.attribute_ids
        self.assertEqual(1, len(single_attribute_ids))
        self.assertEqual(self._timezone.attribute_id, single_attribute_ids[0])

        attribute_ids = self._attribute_set.attribute_ids
        self.assertEqual(3, len(attribute_ids))
        self.assertEqual(
            [self._user_agent.attribute_id, self._timezone.attribute_id,
             self._do_not_track.attribute_id],
            attribute_ids)

    def test_add_new_attribute(self):
        new_attr_set = AttributeSet({self._user_agent})
        self.assertEqual(1, len(new_attr_set))
        new_attribute = ATTRIBUTES[2]
        new_attr_set.add(new_attribute)
        self.assertEqual(2, len(new_attr_set))
        self.assertIn(self._user_agent, new_attr_set)
        self.assertIn(new_attribute, new_attr_set)

    def test_add_new_attribute_already_present(self):
        new_attr_set = AttributeSet({self._user_agent, self._timezone})
        with self.assertRaises(DuplicateAttributeId):
            new_attr_set.add(self._timezone)

    def test_remove(self):
        new_attr_set = AttributeSet({self._user_agent, self._timezone})
        self.assertEqual(2, len(new_attr_set))
        self.assertIn(self._user_agent, new_attr_set)
        self.assertIn(self._timezone, new_attr_set)
        new_attr_set.remove(self._user_agent)
        self.assertEqual(1, len(new_attr_set))
        self.assertIn(self._timezone, new_attr_set)
        self.assertNotIn(self._user_agent, new_attr_set)

    def test_remove_attribute_not_present(self):
        new_attr_set = AttributeSet({self._user_agent, self._timezone})
        self.assertEqual(2, len(new_attr_set))
        self.assertIn(self._user_agent, new_attr_set)
        self.assertIn(self._timezone, new_attr_set)
        non_present_attribute = Attribute(42, 'unknown')
        with self.assertRaises(KeyError):
            new_attr_set.remove(non_present_attribute)
        self.assertEqual(2, len(new_attr_set))
        self.assertIn(self._user_agent, new_attr_set)
        self.assertIn(self._timezone, new_attr_set)

    def test_is_superset(self):
        set_single_attr = AttributeSet({self._user_agent})
        self.assertTrue(self._attribute_set.issuperset(set_single_attr))
        self.assertFalse(set_single_attr.issuperset(self._attribute_set))

    def test_is_superset_empty_set(self):
        self.assertTrue(self._attribute_set.issuperset(self._empty_attr_set))
        self.assertFalse(self._empty_attr_set.issuperset(self._attribute_set))

    def test_is_superset_different_set(self):
        set_another_attr = AttributeSet({Attribute(42, 'unknown'),
                                         self._user_agent})
        self.assertFalse(set_another_attr.issuperset(self._attribute_set))
        self.assertFalse(self._attribute_set.issuperset(set_another_attr))

    def test_is_subset(self):
        set_single_attr = AttributeSet({self._user_agent})
        self.assertFalse(self._attribute_set.issubset(set_single_attr))
        self.assertTrue(set_single_attr.issubset(self._attribute_set))

    def test_is_subset_empty_set(self):
        self.assertFalse(self._attribute_set.issubset(self._empty_attr_set))
        self.assertTrue(self._empty_attr_set.issubset(self._attribute_set))

    def test_is_subset_different_set(self):
        set_another_attr = AttributeSet({Attribute(42, 'unknown'),
                                         self._user_agent})
        self.assertFalse(set_another_attr.issubset(self._attribute_set))
        self.assertFalse(self._attribute_set.issubset(set_another_attr))

    def test_get_attribute_by_id(self):
        self.assertEqual(self._user_agent,
                         self._attribute_set.get_attribute_by_id(
                             self._user_agent.attribute_id))
        self.assertEqual(self._timezone,
                         self._attribute_set.get_attribute_by_id(
                             self._timezone.attribute_id))
        with self.assertRaises(KeyError):
            self._attribute_set.get_attribute_by_id(-1)
        with self.assertRaises(KeyError):
            self._attribute_set.get_attribute_by_id(0)
        with self.assertRaises(KeyError):
            self._attribute_set.get_attribute_by_id(5)

    def test_get_attribute_by_name(self):
        self.assertEqual(
            self._user_agent,
            self._attribute_set.get_attribute_by_name(self._user_agent.name))
        self.assertEqual(
            self._timezone,
            self._attribute_set.get_attribute_by_name(self._timezone.name))
        with self.assertRaises(KeyError):
            self._attribute_set.get_attribute_by_name('')
        with self.assertRaises(KeyError):
            self._attribute_set.get_attribute_by_name('unknown')


if __name__ == '__main__':
    unittest.main()
