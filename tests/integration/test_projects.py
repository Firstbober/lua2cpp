"""Integration tests for multi-file projects"""

import pytest
from pathlib import Path
from lua2c.module_system.dependency_resolver import DependencyResolver, DependencyGraph


class TestProjects:
    """Test suite for multi-file project transpilation"""

    def test_simple_two_module_project(self, tmp_path):
        """Test simple project with two modules"""
        # Create project structure
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Create main.lua
        main = project_dir / "main.lua"
        main.write_text("""
local utils = require("utils")
local result = utils.add(5, 3)
print(result)
return result
""")

        # Create utils.lua
        utils = project_dir / "utils.lua"
        utils.write_text("""
local function add(a, b)
    return a + b
end

return {
    add = add
}
""")

        # Resolve dependencies
        resolver = DependencyResolver(project_dir)
        lua_files = [Path("main.lua"), Path("utils.lua")]
        module_infos = resolver.resolve_project(lua_files)

        # Check modules were found
        assert "main" in module_infos
        assert "utils" in module_infos

        # Check main depends on utils
        main_info = module_infos["main"]
        assert len(main_info.dependencies) == 1
        assert main_info.dependencies[0].module_name == "utils"

        # Build graph and check topological order
        graph = resolver.build_dependency_graph(module_infos)
        order = graph.topological_sort()
        
        # utils should come before main
        assert order.index("utils") < order.index("main")

    def test_dependency_order(self, tmp_path):
        """Test that dependencies are loaded in correct order"""
        project_dir = tmp_path / "test_deps"
        project_dir.mkdir()

        # Create dependency chain: main -> utils -> helper
        (project_dir / "helper.lua").write_text("return {}")
        (project_dir / "utils.lua").write_text("""
local helper = require("helper")
return {}
""")
        (project_dir / "main.lua").write_text("""
local utils = require("utils")
return {}
""")

        # Resolve and build graph
        resolver = DependencyResolver(project_dir)
        lua_files = [Path("main.lua"), Path("utils.lua"), Path("helper.lua")]
        module_infos = resolver.resolve_project(lua_files)
        graph = resolver.build_dependency_graph(module_infos)
        order = graph.topological_sort()

        # Check order: helper -> utils -> main
        assert order == ["helper", "utils", "main"] or order.index("helper") < order.index("utils") < order.index("main")

    def test_nested_directories(self, tmp_path):
        """Test project with nested directory structure"""
        project_dir = tmp_path / "test_nested"
        project_dir.mkdir()
        subdir = project_dir / "subdir"
        subdir.mkdir()

        (subdir / "helper.lua").write_text("return {}")
        (project_dir / "main.lua").write_text("""
local helper = require("subdir.helper")
return {}
""")

        # Resolve
        resolver = DependencyResolver(project_dir)
        lua_files = [Path("main.lua"), Path("subdir/helper.lua")]
        module_infos = resolver.resolve_project(lua_files)

        # Check nested module was found (uses __ separator)
        assert "main" in module_infos
        assert "subdir__helper" in module_infos

        # Check main depends on subdir__helper
        main_info = module_infos["main"]
        assert len(main_info.dependencies) == 1
        assert main_info.dependencies[0].module_name == "subdir__helper"

    def test_module_return_table_of_functions(self, tmp_path):
        """Test that modules returning tables with functions work correctly"""
        project_dir = tmp_path / "test_table_return"
        project_dir.mkdir()

        (project_dir / "mathlib.lua").write_text("""
local function add(a, b) return a + b end
local function sub(a, b) return a - b end
local function mul(a, b) return a * b end

return {
    add = add,
    sub = sub,
    mul = mul
}
""")

        (project_dir / "main.lua").write_text("""
local m = require("mathlib")
local sum = m.add(10, 5)
local diff = m.sub(10, 5)
local prod = m.mul(10, 5)
print(sum, diff, prod)
return {sum, diff, prod}
""")

        # Resolve
        resolver = DependencyResolver(project_dir)
        lua_files = [Path("main.lua"), Path("mathlib.lua")]
        module_infos = resolver.resolve_project(lua_files)

        # Check dependency
        main_info = module_infos["main"]
        assert len(main_info.dependencies) == 1
        assert main_info.dependencies[0].module_name == "mathlib"

    def test_circular_dependency_detection(self, tmp_path):
        """Test that circular dependencies are detected and reported"""
        project_dir = tmp_path / "test_circular"
        project_dir.mkdir()

        # Create circular dependency: a -> b -> a
        (project_dir / "a.lua").write_text('require("b") return {}')
        (project_dir / "b.lua").write_text('require("a") return {}')
        (project_dir / "main.lua").write_text('require("a") return {}')

        # Resolve and build graph
        resolver = DependencyResolver(project_dir)
        lua_files = [Path("main.lua"), Path("a.lua"), Path("b.lua")]
        module_infos = resolver.resolve_project(lua_files)
        graph = resolver.build_dependency_graph(module_infos)

        # Should raise ValueError with circular dependency
        with pytest.raises(ValueError, match="Circular dependency"):
            graph.topological_sort()

    def test_path_to_module_name(self, tmp_path):
        """Test path to module name conversion"""
        project_dir = tmp_path / "test_naming"
        project_dir.mkdir()

        resolver = DependencyResolver(project_dir)

        # Test simple file
        assert resolver._path_to_module_name(Path("utils.lua")) == "utils"

        # Test nested file (uses __ separator)
        assert resolver._path_to_module_name(Path("subdir/helper.lua")) == "subdir__helper"

    def test_require_to_module_name(self, tmp_path):
        """Test require path to module name conversion"""
        project_dir = tmp_path / "test_require"
        project_dir.mkdir()

        resolver = DependencyResolver(project_dir)

        # Test simple require
        assert resolver._require_to_module_name("utils") == "utils"

        # Test dotted require (converts to __ separator)
        assert resolver._require_to_module_name("subdir.helper") == "subdir__helper"

    def test_no_dependencies(self, tmp_path):
        """Test module with no dependencies"""
        project_dir = tmp_path / "test_no_deps"
        project_dir.mkdir()

        (project_dir / "main.lua").write_text("""
local x = 10
print(x)
return x
""")

        # Resolve
        resolver = DependencyResolver(project_dir)
        lua_files = [Path("main.lua")]
        module_infos = resolver.resolve_project(lua_files)

        # Check no dependencies
        main_info = module_infos["main"]
        assert len(main_info.dependencies) == 0

        # Check topological sort still works
        graph = resolver.build_dependency_graph(module_infos)
        order = graph.topological_sort()
        assert order == ["main"]

    def test_multiple_dependencies(self, tmp_path):
        """Test module depending on multiple other modules"""
        project_dir = tmp_path / "test_multiple"
        project_dir.mkdir()

        (project_dir / "a.lua").write_text("return {}")
        (project_dir / "b.lua").write_text("return {}")
        (project_dir / "c.lua").write_text("return {}")
        (project_dir / "main.lua").write_text("""
local a = require("a")
local b = require("b")
local c = require("c")
return {}
""")

        # Resolve
        resolver = DependencyResolver(project_dir)
        lua_files = [Path("main.lua"), Path("a.lua"), Path("b.lua"), Path("c.lua")]
        module_infos = resolver.resolve_project(lua_files)

        # Check dependencies
        main_info = module_infos["main"]
        assert len(main_info.dependencies) == 3

        dep_names = {d.module_name for d in main_info.dependencies}
        assert dep_names == {"a", "b", "c"}

        # Check topological order
        graph = resolver.build_dependency_graph(module_infos)
        order = graph.topological_sort()

        # main should be last
        assert order[-1] == "main"

    def test_complex_dependency_chain(self, tmp_path):
        """Test complex dependency chain: main -> a -> b -> c -> d"""
        project_dir = tmp_path / "test_chain"
        project_dir.mkdir()

        (project_dir / "d.lua").write_text("return {}")
        (project_dir / "c.lua").write_text('require("d") return {}')
        (project_dir / "b.lua").write_text('require("c") return {}')
        (project_dir / "a.lua").write_text('require("b") return {}')
        (project_dir / "main.lua").write_text('require("a") return {}')

        # Resolve
        resolver = DependencyResolver(project_dir)
        lua_files = [Path("main.lua"), Path("a.lua"), Path("b.lua"), Path("c.lua"), Path("d.lua")]
        module_infos = resolver.resolve_project(lua_files)
        graph = resolver.build_dependency_graph(module_infos)
        order = graph.topological_sort()

        # Check order is correct
        expected = ["d", "c", "b", "a", "main"]
        assert order == expected

    def test_get_function_signature(self):
        """Test GlobalTypeRegistry function signature lookup"""
        from lua2c.core.global_type_registry import GlobalTypeRegistry

        # Test library function
        sig = GlobalTypeRegistry.get_function_signature("io.write")
        assert sig is not None
        assert sig.return_type == "void"
        assert "const std::vector<luaValue>&" in sig.param_types

        # Test standalone function
        sig = GlobalTypeRegistry.get_function_signature("tonumber")
        assert sig is not None
        assert sig.return_type == "double"

        # Test non-existent function
        sig = GlobalTypeRegistry.get_function_signature("not.a.real.function")
        assert sig is None

    def test_get_global_type(self):
        """Test GlobalTypeRegistry global type lookup"""
        from lua2c.core.global_type_registry import GlobalTypeRegistry

        # Test special globals
        assert GlobalTypeRegistry.get_global_type("arg") == "luaArray<luaValue>"
        assert GlobalTypeRegistry.get_global_type("_G") == "std::unordered_map<luaValue, luaValue>"

        # Test non-existent global
        assert GlobalTypeRegistry.get_global_type("not_real") is None

    def test_is_library_module(self):
        """Test GlobalTypeRegistry library module check"""
        from lua2c.core.global_type_registry import GlobalTypeRegistry

        assert GlobalTypeRegistry.is_library_module("io")
        assert GlobalTypeRegistry.is_library_module("math")
        assert GlobalTypeRegistry.is_library_module("string")
        assert not GlobalTypeRegistry.is_library_module("not_real")

    def test_get_module_functions(self):
        """Test GlobalTypeRegistry module function list"""
        from lua2c.core.global_type_registry import GlobalTypeRegistry

        math_funcs = GlobalTypeRegistry.get_module_functions("math")
        assert "sqrt" in math_funcs
        assert "abs" in math_funcs

        io_funcs = GlobalTypeRegistry.get_module_functions("io")
        assert "write" in io_funcs
        assert "read" in io_funcs
