"""Draw Window API — Element Registry and ElementName Type.

Declares named elements that can be shared across windows. An element
is declared once and is not tied to a window; a window claims an element
by listing it in its ``elements`` list.

Element and region references are checked lazily — creation order does
not matter and no error is raised at shape-definition time.
"""

from typing import Dict, Optional, Set


class ElementName(str):
    """Tagged string subclass identifying a declared element.

    Returned by ``window.element("name")``. It behaves exactly like a
    plain ``str`` for hashing, equality, and dictionary keying, but
    carries metadata indicating that it was declared through the element
    system. The shape module can test ``isinstance(name, ElementName)``
    to decide whether a shape is also a window element.
    """

    def __new__(cls, name: str) -> "ElementName":
        return super().__new__(cls, name)

    def __repr__(self) -> str:
        return f"ElementName({super().__repr__()})"


class ElementRegistry:
    """Global registry of declared element names.

    * ``declare(name)`` — registers the name and returns an ``ElementName``.
      Calling it again with the same name returns the same tag without error.
    * ``is_declared(name)`` — checks whether the name was declared.
    * ``all_names()`` — returns all declared element names.
    """

    def __init__(self) -> None:
        self._elements: Dict[str, ElementName] = {}

    def declare(self, name: str) -> ElementName:
        """Declares an element name and returns the ``ElementName`` tag.

        Idempotent — calling with an already-declared name returns the
        existing tag.
        """
        if name not in self._elements:
            self._elements[name] = ElementName(name)
        return self._elements[name]

    def is_declared(self, name: str) -> bool:
        """Returns ``True`` if the element name has been declared."""
        return name in self._elements

    def all_names(self) -> Set[str]:
        """Returns a copy of all declared element names."""
        return set(self._elements.keys())

    def clear(self) -> None:
        """Resets the registry (useful for testing)."""
        self._elements.clear()


# Global Singleton Element Registry
GLOBAL_ELEMENT_REGISTRY = ElementRegistry()
