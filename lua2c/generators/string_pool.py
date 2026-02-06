"""String pool management for Lua2C transpiler

Handles static string literal storage to avoid runtime allocation.
All string literals are collected at transpile time and stored
in a static array in the generated C code.
"""

from typing import List, Set


class StringPool:
    """Manages string literals for static allocation"""

    def __init__(self) -> None:
        """Initialize empty string pool"""
        self._strings: List[str] = []
        self._string_set: Set[str] = set()

    def add(self, string: str) -> int:
        """Add a string literal to the pool and return its index

        Args:
            string: String literal to add

        Returns:
            Index of the string in the pool (deduplicated)
        """
        if string in self._string_set:
            return self._strings.index(string)

        index = len(self._strings)
        self._strings.append(string)
        self._string_set.add(string)
        return index

    def get(self, index: int) -> str:
        """Get string by index

        Args:
            index: String index in pool

        Returns:
            String literal

        Raises:
            IndexError: If index is out of bounds
        """
        if index < 0 or index >= len(self._strings):
            raise IndexError(f"String index {index} out of bounds (size: {len(self._strings)})")
        return self._strings[index]

    def index(self, string: str) -> int | None:
        """Get index of a string in the pool

        Args:
            string: String to look up

        Returns:
            Index if found, None otherwise
        """
        if string not in self._string_set:
            return None
        return self._strings.index(string)

    def contains(self, string: str) -> bool:
        """Check if string is in pool

        Args:
            string: String to check

        Returns:
            True if string exists in pool
        """
        return string in self._string_set

    def size(self) -> int:
        """Get number of unique strings in pool

        Returns:
            Number of unique strings
        """
        return len(self._strings)

    def all_strings(self) -> List[str]:
        """Get all strings in order

        Returns:
            List of all strings in pool order
        """
        return list(self._strings)

    def clear(self) -> None:
        """Clear the string pool"""
        self._strings.clear()
        self._string_set.clear()
