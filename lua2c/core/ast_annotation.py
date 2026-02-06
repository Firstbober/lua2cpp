"""AST annotation layer for Lua2C transpiler

Provides a clean way to attach metadata to AST nodes across multiple passes.
Eliminates the need for external caches that depend on object identity.
"""

from typing import Optional, Any
from lua2c.core.type_system import Type


class ASTAnnotationStore:
    """Stores annotations on AST nodes using a private namespace"""

    PREFIX = "_l2c_"

    @staticmethod
    def set_type(node, type_info: Type) -> None:
        """Attach type information to an AST node

        Args:
            node: AST node (any luaparser.astnodes.Node)
            type_info: Type information to attach
        """
        if hasattr(node, '__dict__'):
            setattr(node, f"{ASTAnnotationStore.PREFIX}type", type_info)

    @staticmethod
    def get_type(node) -> Optional[Type]:
        """Get type information from an AST node

        Args:
            node: AST node

        Returns:
            Type information if present, None otherwise
        """
        if hasattr(node, '__dict__'):
            return getattr(node, f"{ASTAnnotationStore.PREFIX}type", None)
        return None

    @staticmethod
    def set_requires_lua_value(node, value: bool) -> None:
        """Mark that a node requires luaValue wrapper

        Args:
            node: AST node
            value: True if luaValue wrapper is required
        """
        if hasattr(node, '__dict__'):
            setattr(node, f"{ASTAnnotationStore.PREFIX}needs_lua", value)

    @staticmethod
    def get_requires_lua_value(node) -> bool:
        """Check if a node requires luaValue wrapper

        Args:
            node: AST node

        Returns:
            True if luaValue wrapper is required
        """
        if hasattr(node, '__dict__'):
            return getattr(node, f"{ASTAnnotationStore.PREFIX}needs_lua", False)
        return False

    @staticmethod
    def set_annotation(node, key: str, value: Any) -> None:
        """Set a custom annotation on a node

        Args:
            node: AST node
            key: Annotation key (will be prefixed)
            value: Annotation value
        """
        if hasattr(node, '__dict__'):
            setattr(node, f"{ASTAnnotationStore.PREFIX}{key}", value)

    @staticmethod
    def get_annotation(node, key: str, default: Any = None) -> Any:
        """Get a custom annotation from a node

        Args:
            node: AST node
            key: Annotation key (will be prefixed)
            default: Default value if not found

        Returns:
            Annotation value or default
        """
        if hasattr(node, '__dict__'):
            return getattr(node, f"{ASTAnnotationStore.PREFIX}{key}", default)
        return default

    @staticmethod
    def has_annotation(node, key: str) -> bool:
        """Check if a node has a specific annotation

        Args:
            node: AST node
            key: Annotation key (will be prefixed)

        Returns:
            True if annotation exists
        """
        if hasattr(node, '__dict__'):
            return hasattr(node, f"{ASTAnnotationStore.PREFIX}{key}")
        return False

    @staticmethod
    def clear_annotations(node) -> None:
        """Remove all annotations from a node

        Args:
            node: AST node
        """
        if hasattr(node, '__dict__'):
            attrs = dir(node)
            prefix = ASTAnnotationStore.PREFIX
            for attr in attrs:
                if attr.startswith(prefix):
                    delattr(node, attr)
