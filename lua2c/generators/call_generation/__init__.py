"""Call generation module
Provides strategy pattern and utilities for function call generation.
"""
from lua2c.generators.call_generation.type_queries import TypeQueryService
from lua2c.generators.call_generation.context import (
    CallGenerationContext,
    CallContextBuilder,
)
from lua2c.generators.call_generation.strategies import (
    CallGenerationStrategy,
    LocalFunctionStrategy,
    LibraryFunctionStrategy,
    StaticLibraryStrategy,
    VariadicLibraryStrategy,
    DefaultCallStrategy,
)

__all__ = [
    'TypeQueryService',
    'CallGenerationContext',
    'CallContextBuilder',
    'CallGenerationStrategy',
    'LocalFunctionStrategy',
    'LibraryFunctionStrategy',
    'StaticLibraryStrategy',
    'VariadicLibraryStrategy',
    'DefaultCallStrategy',
]
