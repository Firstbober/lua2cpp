"""Analyzers for Lua2C transpiler

This module contains various analysis passes that can be run on AST.

Modules:
- TypeInference: Multi-pass type inference with inter-procedural support
- FunctionSignatureRegistry: Tracks function signatures and call sites
- PropagationLogger: Logs type propagation decisions
- TypeValidator: Validates inferred types for consistency
"""

from lua2c.analyzers.type_inference import TypeInference
from lua2c.analyzers.function_registry import (
    FunctionSignatureRegistry, FunctionSignature, CallSiteInfo
)
from lua2c.analyzers.propagation_logger import (
    PropagationLogger, PropagationDirection, PropagationRecord, ConflictRecord
)
from lua2c.analyzers.type_validator import (
    TypeValidator, ValidationSeverity, ValidationIssue
)

__all__ = [
    'TypeInference',
    'FunctionSignatureRegistry',
    'FunctionSignature',
    'CallSiteInfo',
    'PropagationLogger',
    'PropagationDirection',
    'PropagationRecord',
    'ConflictRecord',
    'TypeValidator',
    'ValidationSeverity',
    'ValidationIssue',
]

