#!/usr/bin/python3
"""Module containing the Attribute interface."""

class Attribute:
    """The interface of the Attribute class."""

    def __init__(self, id: int, name: str):
        """Initializes the attribute object with its id and name.

        Args:
            id: The id of the attribute.
            name: The name of the attribute
        """
        self._id = id
        self._name = name

    def __str__(self) -> str:
        """Provides a string representation of this attribute.

        Returns:
            A string representation of this attribute.
        """
        return self.get_name()

    def get_id(self) -> int:
        """Gives the id of the attribute.

        Returns:
            The id of the attribute.
        """
        return self._id

    def get_name(self) -> str:
        """Gives the name of the attribute.

        Returns:
            The name of the attribute.
        """
        return self._name
