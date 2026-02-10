import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class TestProjectStructure:

    def test_directories_exist(self):
        project_root = Path(__file__).parent.parent

        required_dirs = [
            project_root / "lua2cpp" / "core",
            project_root / "lua2cpp" / "analyzers",
            project_root / "tests",
            project_root / "tests" / "integration",
        ]

        for directory in required_dirs:
            assert directory.is_dir(), f"Required directory {directory} does not exist"

    def test_package_structure(self):
        project_root = Path(__file__).parent.parent
        init_file = project_root / "lua2cpp" / "__init__.py"

        assert init_file.is_file(), f"Package __init__.py at {init_file} does not exist"

    def test_pyproject_toml_valid(self):
        project_root = Path(__file__).parent.parent
        pyproject_path = project_root / "pyproject.toml"

        assert pyproject_path.is_file(), f"pyproject.toml at {pyproject_path} does not exist"

        with open(pyproject_path, "rb") as f:
            try:
                config = tomllib.load(f)
                assert "project" in config, "pyproject.toml missing [project] section"
            except Exception as e:
                assert False, f"pyproject.toml is not valid TOML: {e}"
