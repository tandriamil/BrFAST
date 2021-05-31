#!/usr/bin/python3
"""brfast.data.attribute module: Classes related to the attributes."""

from typing import Iterable, Iterator, List, Optional

from sortedcontainers import SortedDict


# ============================== Utility classes ==============================
class DuplicateAttributeId(Exception):
    """Same id attribute already exists in an attribute set."""


# ========================= Attribute related classes =========================
class Attribute:
    """The Attribute class that represents a browser fingerprinting attribute.

    The attributes should have a unique identifier.
    """

    def __init__(self, attribute_id: int, name: str):
        """Initialize the Attribute object with its id and its name.

        Args:
            attribute_id: The unique id of the attribute.
            name: The name of the attribute.
        """
        self._attribute_id = attribute_id
        self._name = name

    def __repr__(self) -> str:
        """Provide a string representation of the attribute.

        Returns:
            A string representation of the attribute.
        """
        return f'{self.__class__.__name__}({self._attribute_id}, {self._name})'

    @property
    def attribute_id(self) -> int:
        """Give the id of the attribute (read only).

        Returns:
            The id of the attribute.
        """
        return self._attribute_id

    @property
    def name(self) -> str:
        """Give the name of the attribute (read only).

        Returns:
            The name of the attribute.
        """
        return self._name

    def __hash__(self) -> int:
        """Give the hash of the attribute which is its id.

        Returns:
            The hash of the attribute which is its id.
        """
        return self._attribute_id

    def __eq__(self, other_attribute: 'Attribute') -> bool:
        """Compare the attribute with another one using the equality operator.

        Args:
            other_attribute: The other attribute to compare the attribute with.

        Returns:
            The attributes are the same (i.e., they share the same id).
        """
        return (isinstance(other_attribute, self.__class__)
                and self._attribute_id == other_attribute.attribute_id)

    def __lt__(self, other_attribute: 'Attribute') -> bool:
        """Compare the attribute with another one using the "<" operator.

        Args:
            other_attribute: The other attribute to compare the attribute with.

        Raises:
            TypeError: The parameter is not an attribute, cannot be compared.

        Returns:
            Whether the other attribute is "lower" given their ids.
            NotImplemented if the parameter is not an Attribute.
        """
        if not isinstance(other_attribute, self.__class__):
            return NotImplemented
        return self.attribute_id < other_attribute.attribute_id


class AttributeSet:
    """The AttributeSet class that represents an attribute set."""

    def __init__(self, attributes: Optional[Iterable[Attribute]] = None):
        """Initialize the AttributeSet object with the attributes.

        Args:
            attributes: The attributes that compose the attribute set if set.

        Raises:
            DuplicateAttributeId: Two attributes share the same id.
        """
        # Maintain a sorted dictionary linking the attributes id to the
        # attribute objects
        self._id_to_attr = SortedDict()
        if attributes:
            for attribute in attributes:
                self.add(attribute)

    def __iter__(self) -> Iterator:
        """Give the iterator for the AttributeSet to get the attributes.

        Returns:
            An iterator that iterates over the Attribute objects that compose
            the attribute set.
        """
        return iter(self._id_to_attr.values())

    def __repr__(self) -> str:
        """Provide a string representation of the attribute set.

        Returns:
            A string representation of the attribute set.
        """
        attribute_list = ', '.join(str(attr)
                                   for attr in self._id_to_attr.values())
        return f'{self.__class__.__name__}([{attribute_list}])'

    @property
    def attribute_names(self) -> List[str]:
        """Give the names of the attributes of this attribute set (read only).

        The attribute names are sorted in function of the attribute ids.

        Returns:
            The name of the attributes of this attribute set as a list of str.
        """
        return list(attribute.name for attribute in self._id_to_attr.values())

    @property
    def attribute_ids(self) -> List[int]:
        """Give the ids of the attributes of this attribute set (read only).

        Returns:
            The ids of the attributes of this set as a sorted list of integers.
        """
        return list(self._id_to_attr.keys())

    def add(self, attribute: Attribute):
        """Add an attribute to this attribute set if it is not already present.

        Args:
            attribute: The attribute to add.

        Raises:
            DuplicateAttributeId: An attribute with the same id as the
                                  attribute that is added already exists.
        """
        if attribute.attribute_id in self._id_to_attr:
            raise DuplicateAttributeId('An attribute with the same id as '
                                       f'{attribute} already exists.')
        self._id_to_attr[attribute.attribute_id] = attribute

    def remove(self, attribute: Attribute):
        """Remove an attribute from this attribute set.

        Args:
            attribute: The attribute to remove.

        Raises:
            KeyError: The attribute is not present in this attribute set.
        """
        if attribute.attribute_id not in self._id_to_attr:
            raise KeyError(f'{attribute} is not among the attributes.')
        del self._id_to_attr[attribute.attribute_id]

    def __hash__(self) -> int:
        """Give the hash of an attribute set: the hash of its attributes.

        Returns:
            The hash of an attribute set as the hash of its frozen attributes.
        """
        return hash(frozenset(self.attribute_ids))

    def __eq__(self, other_attr_set: 'AttributeSet') -> bool:
        """Compare two attribute sets, equal if the attributes correspond.

        Args:
            other_attr_set: The other attribute set to which the attribute set
                            is compared with.

        Returns:
            The two attribute sets are equal: they share the same attributes.
        """
        return (isinstance(other_attr_set, self.__class__)
                and hash(self) == hash(other_attr_set))

    def __contains__(self, attribute: Attribute) -> bool:
        """Check if the attribute is in the attribute set.

        Args:
            attribute: The attribute that is checked whether it is in this set.

        Returns:
            The attribute is in the attribute set.
        """
        return attribute.attribute_id in self._id_to_attr

    def __len__(self) -> int:
        """Give the size of this attribute set as the number of attributes.

        Returns:
            The number of attributes in this attribute set.
        """
        return len(self._id_to_attr)

    def issuperset(self, other_attribute_set: 'AttributeSet') -> bool:
        """Check if the attribute set is a superset of the one in parameters.

        Args:
            other_attribute_set: The attribute set for which we check whether
                                 the attribute set is a superset of.

        Returns:
            The attribute set is a superset of the other attribute set.
        """
        self_attribute_ids_set = frozenset(self.attribute_ids)
        other_attribute_ids_set = frozenset(other_attribute_set.attribute_ids)
        return self_attribute_ids_set.issuperset(other_attribute_ids_set)

    def issubset(self, other_attribute_set: 'AttributeSet') -> bool:
        """Check if the attribute set is a subset of the one in parameters.

        Args:
            other_attribute_set: The attribute set for which we check whether
                                 the attribute set is a subset of.

        Returns:
            The attribute set is a subset of the other attribute set.
        """
        self_attribute_ids_set = frozenset(self.attribute_ids)
        other_attribute_ids_set = frozenset(other_attribute_set.attribute_ids)
        return self_attribute_ids_set.issubset(other_attribute_ids_set)

    def get_attribute_by_id(self, attribute_id: int) -> Attribute:
        """Give an attribute by its id.

        Args:
            attribute_id: The id of the attribute to retrieve.

        Raises:
            KeyError: The attribute is not present in this attribute set.
        """
        if attribute_id not in self._id_to_attr:
            raise KeyError(f'No attribute with the id {attribute_id}.')
        return self._id_to_attr[attribute_id]

    def get_attribute_by_name(self, name: str) -> Attribute:
        """Give an attribute by its name.

        Args:
            name: The name of the attribute to retrieve.

        Raises:
            KeyError: The attribute is not present in this attribute set.
        """
        for attribute in self._id_to_attr.values():
            if attribute.name == name:
                return attribute
        raise KeyError(f'No attribute is named {name}.')
