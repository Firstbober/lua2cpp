"""Global type registry for Lua2C transpiler

Defines type signatures for all Lua globals and library functions.
Used to generate custom state classes with typed members.
"""

from dataclasses import dataclass
from typing import List, Dict, Set, Optional
from enum import Enum


@dataclass
class FunctionSignature:
    """C++ function signature for Lua library function"""

    return_type: str
    param_types: List[str]
    cpp_signature: str  # Full C++ signature including function pointer syntax


class LibraryModule(Enum):
    """Lua standard library modules"""

    IO = "io"
    STRING = "string"
    MATH = "math"
    TABLE = "table"
    OS = "os"


class GlobalTypeRegistry:
    """Registry of type signatures for Lua globals and library functions"""

    # Special Lua globals with their C++ types
    SPECIAL_GLOBALS: Dict[str, str] = {
        "arg": "luaArray<luaValue>",
        "_G": "std::unordered_map<luaValue, luaValue>",
    }

    # Library function signatures
    # Format: "module.function" -> FunctionSignature
    LIBRARY_FUNCTIONS: Dict[str, FunctionSignature] = {
        # IO library
        "io.write": FunctionSignature(
            return_type="void",
            param_types=["const std::vector<luaValue>&"],
            cpp_signature="void(*)(const std::vector<luaValue>&)",
        ),
        "io.read": FunctionSignature(
            return_type="std::string",
            param_types=["const std::string&"],
            cpp_signature="std::string(*)(const std::string&)",
        ),
        "io.flush": FunctionSignature(
            return_type="void", param_types=[], cpp_signature="void(*)()"
        ),
        # String library
        "string.format": FunctionSignature(
            return_type="std::string",
            param_types=["const std::string&", "const std::vector<luaValue>&"],
            cpp_signature="std::string(*)(const std::string&, const std::vector<luaValue>&)",
        ),
        "string.len": FunctionSignature(
            return_type="double",
            param_types=["const std::string&"],
            cpp_signature="double(*)(const std::string&)",
        ),
        "string.sub": FunctionSignature(
            return_type="std::string",
            param_types=["const std::string&", "double", "double"],
            cpp_signature="std::string(*)(const std::string&, double, double)",
        ),
        "string.upper": FunctionSignature(
            return_type="std::string",
            param_types=["const std::string&"],
            cpp_signature="std::string(*)(const std::string&)",
        ),
        "string.lower": FunctionSignature(
            return_type="std::string",
            param_types=["const std::string&"],
            cpp_signature="std::string(*)(const std::string&)",
        ),
        # Math library
        "math.sqrt": FunctionSignature(
            return_type="double", param_types=["double"], cpp_signature="double(*)(double)"
        ),
        "math.abs": FunctionSignature(
            return_type="double", param_types=["double"], cpp_signature="double(*)(double)"
        ),
        "math.floor": FunctionSignature(
            return_type="double", param_types=["double"], cpp_signature="double(*)(double)"
        ),
        "math.ceil": FunctionSignature(
            return_type="double", param_types=["double"], cpp_signature="double(*)(double)"
        ),
        "math.sin": FunctionSignature(
            return_type="double", param_types=["double"], cpp_signature="double(*)(double)"
        ),
        "math.cos": FunctionSignature(
            return_type="double", param_types=["double"], cpp_signature="double(*)(double)"
        ),
        "math.tan": FunctionSignature(
            return_type="double", param_types=["double"], cpp_signature="double(*)(double)"
        ),
        "math.log": FunctionSignature(
            return_type="double", param_types=["double"], cpp_signature="double(*)(double)"
        ),
        "math.exp": FunctionSignature(
            return_type="double", param_types=["double"], cpp_signature="double(*)(double)"
        ),
        "math.min": FunctionSignature(
            return_type="double",
            param_types=["double", "double"],
            cpp_signature="double(*)(double, double)",
        ),
        "math.max": FunctionSignature(
            return_type="double",
            param_types=["double", "double"],
            cpp_signature="double(*)(double, double)",
        ),
        "math.random": FunctionSignature(
            return_type="double", param_types=[], cpp_signature="double(*)()"
        ),
        "math.randomseed": FunctionSignature(
            return_type="double", param_types=["double"], cpp_signature="double(*)(double)"
        ),
        # Table library
        "table.unpack": FunctionSignature(
            return_type="luaValue",
            param_types=["const std::vector<luaValue>&"],
            cpp_signature="luaValue(*)(const std::vector<luaValue>&)",
        ),
        # OS library
        "os.clock": FunctionSignature(
            return_type="double", param_types=[], cpp_signature="double(*)()"
        ),
        "os.time": FunctionSignature(
            return_type="double", param_types=[], cpp_signature="double(*)()"
        ),
        "os.date": FunctionSignature(
            return_type="std::string",
            param_types=["const std::string&"],
            cpp_signature="std::string(*)(const std::string&)",
        ),
    }

    # Standalone functions (not in modules)
    STANDALONE_FUNCTIONS: Dict[str, FunctionSignature] = {
        "tonumber": FunctionSignature(
            return_type="double",
            param_types=["const luaValue&"],
            cpp_signature="double(*)(const luaValue&)",
        ),
        "print": FunctionSignature(
            return_type="void",
            param_types=["const std::vector<luaValue>&"],
            cpp_signature="void(*)(const std::vector<luaValue>&)",
        ),
    }

    # Module organization
    LIBRARY_MODULES: Dict[LibraryModule, Set[str]] = {
        LibraryModule.IO: {"write", "read", "flush"},
        LibraryModule.STRING: {"format", "len", "sub", "upper", "lower"},
        LibraryModule.MATH: {
            "sqrt",
            "abs",
            "floor",
            "ceil",
            "sin",
            "cos",
            "tan",
            "log",
            "exp",
            "min",
            "max",
            "random",
            "randomseed",
        },
        LibraryModule.TABLE: {"unpack"},
        LibraryModule.OS: {"clock", "time", "date"},
    }

    @classmethod
    def get_global_type(cls, name: str) -> Optional[str]:
        """Get C++ type for a global variable

        Args:
            name: Global variable name

        Returns:
            C++ type string or None if not a special global
        """
        return cls.SPECIAL_GLOBALS.get(name)

    @classmethod
    def get_function_signature(cls, func_path: str) -> Optional[FunctionSignature]:
        """Get function signature for library function

        Args:
            func_path: Function path like "io.write" or "tonumber"

        Returns:
            FunctionSignature or None if not found
        """
        # Check module functions
        sig = cls.LIBRARY_FUNCTIONS.get(func_path)
        if sig:
            return sig

        # Check standalone functions
        sig = cls.STANDALONE_FUNCTIONS.get(func_path)
        if sig:
            return sig

        return None

    @classmethod
    def is_library_module(cls, name: str) -> bool:
        """Check if name is a library module

        Args:
            name: Module name like "io", "math", etc.

        Returns:
            True if library module
        """
        try:
            LibraryModule(name.lower())
            return True
        except ValueError:
            return False

    @classmethod
    def get_module_functions(cls, module_name: str) -> Set[str]:
        """Get all functions in a library module

        Args:
            module_name: Module name like "io", "math", etc.

        Returns:
            Set of function names in module
        """
        try:
            module = LibraryModule(module_name.lower())
            return cls.LIBRARY_MODULES.get(module, set())
        except ValueError:
            return set()

    @classmethod
    def is_library_function(cls, func_path: str) -> bool:
        """Check if name is a library function path

        Args:
            func_path: Function path like "io.write" or "tonumber"

        Returns:
            True if library function
        """
        return func_path in cls.LIBRARY_FUNCTIONS or func_path in cls.STANDALONE_FUNCTIONS
