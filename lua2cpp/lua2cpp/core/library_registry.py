"""Library function registry for Lua standard library detection

Defines data structures for detecting and describing Lua standard library functions.
Provides lookup methods for library function metadata during transpilation.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
from lua2cpp.core.types import TypeKind


@dataclass
class LibraryFunction:
    """Metadata for a Lua standard library function

    Attributes:
        module: Library module name (e.g., "io", "math", "string")
        name: Function name within the module (e.g., "write", "sqrt", "format")
        return_type: Return type of the function
        params: List of parameter types (for known signatures)
        cpp_name: C++ function name (e.g., "io_write", "math_sqrt")
    """
    module: str
    name: str
    return_type: TypeKind
    params: List[TypeKind]
    cpp_name: str


class LibraryFunctionRegistry:
    """Registry of all Lua standard library functions

    Provides methods to check if a function call is from a standard library
    and retrieve metadata about library functions.
    """

    # Standard library module names
    STANDARD_LIBRARIES = {
        "io", "string", "math", "table",
        "os", "package", "debug", "coroutine"
    }

    def __init__(self) -> None:
        """Initialize registry with all standard library functions"""
        self._functions: Dict[str, Dict[str, LibraryFunction]] = {}
        self._initialize_libraries()

    def _initialize_libraries(self) -> None:
        """Initialize all standard library function definitions"""
        self._initialize_io()
        self._initialize_string()
        self._initialize_math()
        self._initialize_table()
        self._initialize_os()
        self._initialize_package()
        self._initialize_debug()
        self._initialize_coroutine()

    def _initialize_io(self) -> None:
        """Initialize io library functions"""
        io_funcs = [
            LibraryFunction("io", "close", TypeKind.BOOLEAN, [], "io_close"),
            LibraryFunction("io", "flush", TypeKind.BOOLEAN, [], "io_flush"),
            LibraryFunction("io", "input", TypeKind.STRING, [], "io_input"),
            LibraryFunction("io", "lines", TypeKind.FUNCTION, [], "io_lines"),
            LibraryFunction("io", "open", TypeKind.TABLE, [TypeKind.STRING, TypeKind.STRING], "io_open"),
            LibraryFunction("io", "output", TypeKind.STRING, [], "io_output"),
            LibraryFunction("io", "popen", TypeKind.FUNCTION, [TypeKind.STRING, TypeKind.STRING], "io_popen"),
            LibraryFunction("io", "read", TypeKind.STRING, [], "io_read"),
            LibraryFunction("io", "type", TypeKind.STRING, [], "io_type"),
            LibraryFunction("io", "write", TypeKind.BOOLEAN, [], "io_write"),
        ]
        for func in io_funcs:
            self._add_function(func)

    def _initialize_string(self) -> None:
        """Initialize string library functions"""
        string_funcs = [
            LibraryFunction("string", "byte", TypeKind.NUMBER, [TypeKind.STRING, TypeKind.NUMBER, TypeKind.NUMBER], "string_byte"),
            LibraryFunction("string", "char", TypeKind.STRING, [TypeKind.NUMBER, TypeKind.NUMBER, TypeKind.NUMBER], "string_char"),
            LibraryFunction("string", "dump", TypeKind.STRING, [TypeKind.FUNCTION, TypeKind.BOOLEAN], "string_dump"),
            LibraryFunction("string", "find", TypeKind.VARIANT, [TypeKind.STRING, TypeKind.STRING, TypeKind.NUMBER, TypeKind.BOOLEAN], "string_find"),
            LibraryFunction("string", "format", TypeKind.STRING, [TypeKind.STRING, TypeKind.VARIANT, TypeKind.VARIANT, TypeKind.VARIANT], "string_format"),
            LibraryFunction("string", "gmatch", TypeKind.FUNCTION, [TypeKind.STRING, TypeKind.STRING], "string_gmatch"),
            LibraryFunction("string", "gsub", TypeKind.STRING, [TypeKind.STRING, TypeKind.STRING, TypeKind.VARIANT, TypeKind.NUMBER], "string_gsub"),
            LibraryFunction("string", "len", TypeKind.NUMBER, [TypeKind.STRING], "string_len"),
            LibraryFunction("string", "lower", TypeKind.STRING, [TypeKind.STRING], "string_lower"),
            LibraryFunction("string", "match", TypeKind.VARIANT, [TypeKind.STRING, TypeKind.STRING, TypeKind.NUMBER], "string_match"),
            LibraryFunction("string", "pack", TypeKind.STRING, [TypeKind.STRING, TypeKind.VARIANT, TypeKind.VARIANT], "string_pack"),
            LibraryFunction("string", "packsize", TypeKind.NUMBER, [TypeKind.STRING], "string_packsize"),
            LibraryFunction("string", "rep", TypeKind.STRING, [TypeKind.STRING, TypeKind.NUMBER, TypeKind.NUMBER], "string_rep"),
            LibraryFunction("string", "reverse", TypeKind.STRING, [TypeKind.STRING], "string_reverse"),
            LibraryFunction("string", "sub", TypeKind.STRING, [TypeKind.STRING, TypeKind.NUMBER, TypeKind.NUMBER], "string_sub"),
            LibraryFunction("string", "unpack", TypeKind.VARIANT, [TypeKind.STRING, TypeKind.STRING, TypeKind.NUMBER], "string_unpack"),
            LibraryFunction("string", "upper", TypeKind.STRING, [TypeKind.STRING], "string_upper"),
        ]
        for func in string_funcs:
            self._add_function(func)

    def _initialize_math(self) -> None:
        """Initialize math library functions"""
        math_funcs = [
            LibraryFunction("math", "abs", TypeKind.NUMBER, [TypeKind.NUMBER], "math_abs"),
            LibraryFunction("math", "acos", TypeKind.NUMBER, [TypeKind.NUMBER], "math_acos"),
            LibraryFunction("math", "asin", TypeKind.NUMBER, [TypeKind.NUMBER], "math_asin"),
            LibraryFunction("math", "atan", TypeKind.NUMBER, [TypeKind.NUMBER, TypeKind.NUMBER], "math_atan"),
            LibraryFunction("math", "atan2", TypeKind.NUMBER, [TypeKind.NUMBER, TypeKind.NUMBER], "math_atan2"),
            LibraryFunction("math", "ceil", TypeKind.NUMBER, [TypeKind.NUMBER], "math_ceil"),
            LibraryFunction("math", "cos", TypeKind.NUMBER, [TypeKind.NUMBER], "math_cos"),
            LibraryFunction("math", "cosh", TypeKind.NUMBER, [TypeKind.NUMBER], "math_cosh"),
            LibraryFunction("math", "deg", TypeKind.NUMBER, [TypeKind.NUMBER], "math_deg"),
            LibraryFunction("math", "exp", TypeKind.NUMBER, [TypeKind.NUMBER], "math_exp"),
            LibraryFunction("math", "floor", TypeKind.NUMBER, [TypeKind.NUMBER], "math_floor"),
            LibraryFunction("math", "fmod", TypeKind.NUMBER, [TypeKind.NUMBER, TypeKind.NUMBER], "math_fmod"),
            LibraryFunction("math", "frexp", TypeKind.NUMBER, [TypeKind.NUMBER], "math_frexp"),
            LibraryFunction("math", "huge", TypeKind.NUMBER, [], "math_huge"),
            LibraryFunction("math", "ldexp", TypeKind.NUMBER, [TypeKind.NUMBER, TypeKind.NUMBER], "math_ldexp"),
            LibraryFunction("math", "log", TypeKind.NUMBER, [TypeKind.NUMBER, TypeKind.NUMBER], "math_log"),
            LibraryFunction("math", "log10", TypeKind.NUMBER, [TypeKind.NUMBER], "math_log10"),
            LibraryFunction("math", "max", TypeKind.NUMBER, [TypeKind.NUMBER, TypeKind.NUMBER, TypeKind.NUMBER], "math_max"),
            LibraryFunction("math", "maxinteger", TypeKind.NUMBER, [], "math_maxinteger"),
            LibraryFunction("math", "min", TypeKind.NUMBER, [TypeKind.NUMBER, TypeKind.NUMBER, TypeKind.NUMBER], "math_min"),
            LibraryFunction("math", "mininteger", TypeKind.NUMBER, [], "math_mininteger"),
            LibraryFunction("math", "modf", TypeKind.NUMBER, [TypeKind.NUMBER], "math_modf"),
            LibraryFunction("math", "pi", TypeKind.NUMBER, [], "math_pi"),
            LibraryFunction("math", "pow", TypeKind.NUMBER, [TypeKind.NUMBER, TypeKind.NUMBER], "math_pow"),
            LibraryFunction("math", "rad", TypeKind.NUMBER, [TypeKind.NUMBER], "math_rad"),
            LibraryFunction("math", "random", TypeKind.NUMBER, [TypeKind.NUMBER, TypeKind.NUMBER], "math_random"),
            LibraryFunction("math", "randomseed", TypeKind.NUMBER, [TypeKind.NUMBER], "math_randomseed"),
            LibraryFunction("math", "sin", TypeKind.NUMBER, [TypeKind.NUMBER], "math_sin"),
            LibraryFunction("math", "sinh", TypeKind.NUMBER, [TypeKind.NUMBER], "math_sinh"),
            LibraryFunction("math", "sqrt", TypeKind.NUMBER, [TypeKind.NUMBER], "math_sqrt"),
            LibraryFunction("math", "tan", TypeKind.NUMBER, [TypeKind.NUMBER], "math_tan"),
            LibraryFunction("math", "tanh", TypeKind.NUMBER, [TypeKind.NUMBER], "math_tanh"),
            LibraryFunction("math", "tointeger", TypeKind.NUMBER, [TypeKind.VARIANT, TypeKind.NUMBER], "math_tointeger"),
            LibraryFunction("math", "type", TypeKind.STRING, [TypeKind.VARIANT], "math_type"),
            LibraryFunction("math", "ult", TypeKind.BOOLEAN, [TypeKind.NUMBER, TypeKind.NUMBER], "math_ult"),
        ]
        for func in math_funcs:
            self._add_function(func)

    def _initialize_table(self) -> None:
        """Initialize table library functions"""
        table_funcs = [
            LibraryFunction("table", "concat", TypeKind.STRING, [TypeKind.TABLE, TypeKind.STRING, TypeKind.NUMBER, TypeKind.NUMBER], "table_concat"),
            LibraryFunction("table", "insert", TypeKind.BOOLEAN, [TypeKind.TABLE, TypeKind.NUMBER, TypeKind.VARIANT], "table_insert"),
            LibraryFunction("table", "move", TypeKind.TABLE, [TypeKind.TABLE, TypeKind.NUMBER, TypeKind.NUMBER, TypeKind.NUMBER, TypeKind.TABLE], "table_move"),
            LibraryFunction("table", "pack", TypeKind.TABLE, [TypeKind.VARIANT, TypeKind.VARIANT], "table_pack"),
            LibraryFunction("table", "remove", TypeKind.VARIANT, [TypeKind.TABLE, TypeKind.NUMBER], "table_remove"),
            LibraryFunction("table", "sort", TypeKind.BOOLEAN, [TypeKind.TABLE, TypeKind.FUNCTION], "table_sort"),
            LibraryFunction("table", "unpack", TypeKind.VARIANT, [TypeKind.TABLE, TypeKind.NUMBER, TypeKind.NUMBER], "table_unpack"),
        ]
        for func in table_funcs:
            self._add_function(func)

    def _initialize_os(self) -> None:
        """Initialize os library functions"""
        os_funcs = [
            LibraryFunction("os", "clock", TypeKind.NUMBER, [], "os_clock"),
            LibraryFunction("os", "date", TypeKind.STRING, [TypeKind.STRING, TypeKind.NUMBER], "os_date"),
            LibraryFunction("os", "difftime", TypeKind.NUMBER, [TypeKind.NUMBER, TypeKind.NUMBER], "os_difftime"),
            LibraryFunction("os", "execute", TypeKind.BOOLEAN, [TypeKind.STRING], "os_execute"),
            LibraryFunction("os", "exit", TypeKind.BOOLEAN, [TypeKind.BOOLEAN, TypeKind.BOOLEAN], "os_exit"),
            LibraryFunction("os", "getenv", TypeKind.STRING, [TypeKind.STRING], "os_getenv"),
            LibraryFunction("os", "remove", TypeKind.BOOLEAN, [TypeKind.STRING], "os_remove"),
            LibraryFunction("os", "rename", TypeKind.BOOLEAN, [TypeKind.STRING, TypeKind.STRING], "os_rename"),
            LibraryFunction("os", "setlocale", TypeKind.STRING, [TypeKind.STRING, TypeKind.STRING], "os_setlocale"),
            LibraryFunction("os", "time", TypeKind.NUMBER, [TypeKind.TABLE], "os_time"),
            LibraryFunction("os", "tmpname", TypeKind.STRING, [], "os_tmpname"),
        ]
        for func in os_funcs:
            self._add_function(func)

    def _initialize_package(self) -> None:
        """Initialize package library functions"""
        package_funcs = [
            LibraryFunction("package", "loadlib", TypeKind.FUNCTION, [TypeKind.STRING, TypeKind.STRING], "package_loadlib"),
            LibraryFunction("package", "searchpath", TypeKind.STRING, [TypeKind.STRING, TypeKind.STRING, TypeKind.STRING, TypeKind.STRING], "package_searchpath"),
            LibraryFunction("package", "seeall", TypeKind.BOOLEAN, [TypeKind.TABLE], "package_seeall"),
        ]
        for func in package_funcs:
            self._add_function(func)

    def _initialize_debug(self) -> None:
        """Initialize debug library functions"""
        debug_funcs = [
            LibraryFunction("debug", "debug", TypeKind.BOOLEAN, [], "debug_debug"),
            LibraryFunction("debug", "getfenv", TypeKind.TABLE, [TypeKind.VARIANT], "debug_getfenv"),
            LibraryFunction("debug", "gethook", TypeKind.VARIANT, [TypeKind.VARIANT], "debug_gethook"),
            LibraryFunction("debug", "getinfo", TypeKind.TABLE, [TypeKind.VARIANT, TypeKind.STRING], "debug_getinfo"),
            LibraryFunction("debug", "getlocal", TypeKind.VARIANT, [TypeKind.VARIANT, TypeKind.VARIANT], "debug_getlocal"),
            LibraryFunction("debug", "getmetatable", TypeKind.TABLE, [TypeKind.VARIANT], "debug_getmetatable"),
            LibraryFunction("debug", "getregistry", TypeKind.TABLE, [], "debug_getregistry"),
            LibraryFunction("debug", "getupvalue", TypeKind.VARIANT, [TypeKind.VARIANT, TypeKind.NUMBER], "debug_getupvalue"),
            LibraryFunction("debug", "getuservalue", TypeKind.VARIANT, [TypeKind.VARIANT, TypeKind.NUMBER], "debug_getuservalue"),
            LibraryFunction("debug", "setfenv", TypeKind.BOOLEAN, [TypeKind.VARIANT, TypeKind.VARIANT], "debug_setfenv"),
            LibraryFunction("debug", "sethook", TypeKind.BOOLEAN, [TypeKind.VARIANT, TypeKind.STRING, TypeKind.NUMBER], "debug_sethook"),
            LibraryFunction("debug", "setlocal", TypeKind.STRING, [TypeKind.VARIANT, TypeKind.VARIANT, TypeKind.VARIANT], "debug_setlocal"),
            LibraryFunction("debug", "setmetatable", TypeKind.TABLE, [TypeKind.VARIANT, TypeKind.VARIANT], "debug_setmetatable"),
            LibraryFunction("debug", "setupvalue", TypeKind.BOOLEAN, [TypeKind.VARIANT, TypeKind.NUMBER, TypeKind.VARIANT], "debug_setupvalue"),
            LibraryFunction("debug", "setuservalue", TypeKind.BOOLEAN, [TypeKind.VARIANT, TypeKind.VARIANT, TypeKind.NUMBER], "debug_setuservalue"),
            LibraryFunction("debug", "traceback", TypeKind.STRING, [TypeKind.VARIANT, TypeKind.STRING, TypeKind.NUMBER], "debug_traceback"),
            LibraryFunction("debug", "upvalueid", TypeKind.VARIANT, [TypeKind.VARIANT, TypeKind.NUMBER], "debug_upvalueid"),
            LibraryFunction("debug", "upvaluejoin", TypeKind.BOOLEAN, [TypeKind.VARIANT, TypeKind.NUMBER, TypeKind.VARIANT, TypeKind.NUMBER], "debug_upvaluejoin"),
        ]
        for func in debug_funcs:
            self._add_function(func)

    def _initialize_coroutine(self) -> None:
        """Initialize coroutine library functions"""
        coroutine_funcs = [
            LibraryFunction("coroutine", "create", TypeKind.FUNCTION, [TypeKind.FUNCTION], "coroutine_create"),
            LibraryFunction("coroutine", "isyieldable", TypeKind.BOOLEAN, [], "coroutine_isyieldable"),
            LibraryFunction("coroutine", "resume", TypeKind.VARIANT, [TypeKind.VARIANT, TypeKind.VARIANT, TypeKind.VARIANT], "coroutine_resume"),
            LibraryFunction("coroutine", "running", TypeKind.VARIANT, [], "coroutine_running"),
            LibraryFunction("coroutine", "status", TypeKind.STRING, [TypeKind.VARIANT], "coroutine_status"),
            LibraryFunction("coroutine", "wrap", TypeKind.FUNCTION, [TypeKind.FUNCTION], "coroutine_wrap"),
            LibraryFunction("coroutine", "yield", TypeKind.VARIANT, [TypeKind.VARIANT, TypeKind.VARIANT], "coroutine_yield"),
        ]
        for func in coroutine_funcs:
            self._add_function(func)

    def _add_function(self, func: LibraryFunction) -> None:
        """Add a function to the registry

        Args:
            func: LibraryFunction to add
        """
        if func.module not in self._functions:
            self._functions[func.module] = {}
        self._functions[func.module][func.name] = func

    def is_library_function(self, module_name: str, func_name: str) -> bool:
        """Check if a function is from a standard library

        Args:
            module_name: Library module name (e.g., "io", "math")
            func_name: Function name within the module (e.g., "write", "sqrt")

        Returns:
            True if the function is from a standard library, False otherwise
        """
        return module_name in self._functions and func_name in self._functions[module_name]

    def get_library_info(self, module_name: str, func_name: str) -> Optional[LibraryFunction]:
        """Get metadata for a library function

        Args:
            module_name: Library module name (e.g., "io", "math")
            func_name: Function name within the module (e.g., "write", "sqrt")

        Returns:
            LibraryFunction if found, None otherwise
        """
        if module_name in self._functions and func_name in self._functions[module_name]:
            return self._functions[module_name][func_name]
        return None

    def get_all_modules(self) -> List[str]:
        """Get list of all registered library modules

        Returns:
            List of module names
        """
        return list(self._functions.keys())

    def get_module_functions(self, module_name: str) -> List[LibraryFunction]:
        """Get all functions in a module

        Args:
            module_name: Library module name

        Returns:
            List of LibraryFunction objects for the module
        """
        if module_name not in self._functions:
            return []
        return list(self._functions[module_name].values())

    def is_standard_library(self, module_name: str) -> bool:
        """Check if a module name is a standard library

        Args:
            module_name: Module name to check

        Returns:
            True if module is a standard library, False otherwise
        """
        return module_name in self.STANDARD_LIBRARIES
