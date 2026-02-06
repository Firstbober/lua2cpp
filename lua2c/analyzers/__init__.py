"""Analyzers for Lua2C transpiler

This module contains various analysis passes that can be run on the AST.
"""

from lua2c.analyzers.type_inference import TypeInference

__all__ = ['TypeInference']
