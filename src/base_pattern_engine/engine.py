"""Self-copy implementation for one-way package instantiation."""

from __future__ import annotations

import keyword
import re
import shutil
from pathlib import Path

SOURCE_MODULE_NAME = "base_pattern_engine"
SOURCE_DISTRIBUTION_NAME = "base-pattern-engine"
SOURCE_TITLE = "Base Pattern Engine"
SUPPORTED_LICENSES = {"MIT"}
ROOT_FILE_NAMES = ("pyproject.toml", "LICENSE", "README.md")
GENERATED_INIT_TEMPLATE = '''"""Generated standalone package."""

from .core import PACKAGE_NAME, print_package_name

__all__ = ["PACKAGE_NAME", "print_package_name"]

__version__ = "0.1.0"
'''
IGNORED_COPY_PATTERNS = (
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.egg-info",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
)


def instantiate(
    package_name: str,
    output_path: str = ".",
    license_type: str = "MIT",
    overwrite: bool = False,
) -> Path:
    """Create a new standalone Python package from this installed package."""

    module_name = _normalize_module_name(package_name)
    distribution_name = module_name.replace("_", "-")
    package_title = _title_from_module_name(module_name)
    normalized_license = license_type.strip().upper()

    if normalized_license not in SUPPORTED_LICENSES:
        supported = ", ".join(sorted(SUPPORTED_LICENSES))
        raise ValueError(f"Unsupported license '{license_type}'. Supported licenses: {supported}.")

    source_package_dir = Path(__file__).resolve().parent
    metadata_source_dir = _metadata_source_dir(source_package_dir)
    project_dir = Path(output_path).expanduser().resolve() / module_name

    if project_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"Output path already exists: {project_dir}. Use overwrite=True or --overwrite to replace it."
            )
        if not project_dir.is_dir():
            raise FileExistsError(f"Output path exists and is not a directory: {project_dir}")
        shutil.rmtree(project_dir)

    src_dir = project_dir / "src"
    destination_package_dir = src_dir / module_name

    project_dir.mkdir(parents=True)
    src_dir.mkdir()

    _copy_project_files(metadata_source_dir, source_package_dir, project_dir)

    shutil.copytree(
        source_package_dir,
        destination_package_dir,
        ignore=shutil.ignore_patterns(*IGNORED_COPY_PATTERNS),
    )

    replacements = {
        "<package_import_name>": module_name,
        "<package_distribution_name>": distribution_name,
        "<package_title>": package_title,
        SOURCE_MODULE_NAME: module_name,
        SOURCE_DISTRIBUTION_NAME: distribution_name,
        SOURCE_TITLE: package_title,
    }
    _rewrite_text_files(project_dir, replacements)
    _strip_instantiation_interface(project_dir, destination_package_dir)

    return project_dir


def _metadata_source_dir(source_package_dir: Path) -> Path:
    source_project_root = _find_source_project_root(source_package_dir)
    candidate_dir = source_project_root or source_package_dir / "_self"

    missing_files = [
        root_file_name
        for root_file_name in ROOT_FILE_NAMES
        if not (candidate_dir / root_file_name).is_file()
    ]
    if missing_files:
        missing_list = ", ".join(missing_files)
        raise ValueError(f"Cannot locate package metadata files: {missing_list}")

    return candidate_dir


def _copy_project_files(metadata_source_dir: Path, source_package_dir: Path, project_dir: Path) -> None:
    for root_file_name in ROOT_FILE_NAMES:
        source_path = metadata_source_dir / root_file_name
        if root_file_name == "README.md":
            source_path = source_package_dir / "_self" / "README.md"
        shutil.copy2(source_path, project_dir / root_file_name)


def _find_source_project_root(source_package_dir: Path) -> Path | None:
    for candidate_dir in source_package_dir.parents:
        pyproject_path = candidate_dir / "pyproject.toml"
        package_path = candidate_dir / "src" / SOURCE_MODULE_NAME
        if pyproject_path.is_file() and package_path.is_dir():
            return candidate_dir

    return None


def _normalize_module_name(package_name: str) -> str:
    module_name = package_name.strip().replace("-", "_").lower()

    if not module_name:
        raise ValueError("Package name cannot be empty.")
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", module_name):
        raise ValueError(
            "Package name must be a valid Python identifier after replacing '-' with '_'."
        )
    if keyword.iskeyword(module_name):
        raise ValueError(f"Package name cannot be a Python keyword: {module_name}")

    return module_name


def _title_from_module_name(module_name: str) -> str:
    return " ".join(part.capitalize() for part in module_name.split("_") if part)


def _rewrite_text_files(project_dir: Path, replacements: dict[str, str]) -> None:
    for file_path in project_dir.rglob("*"):
        if not file_path.is_file():
            continue

        try:
            original_text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        updated_text = original_text
        for old_value, new_value in replacements.items():
            updated_text = updated_text.replace(old_value, new_value)

        if updated_text != original_text:
            file_path.write_text(updated_text, encoding="utf-8")


def _strip_instantiation_interface(project_dir: Path, package_dir: Path) -> None:
    for relative_path in ("engine.py", "cli.py"):
        file_path = package_dir / relative_path
        if file_path.exists():
            file_path.unlink()

    bundled_metadata_dir = package_dir / "_self"
    if bundled_metadata_dir.exists():
        shutil.rmtree(bundled_metadata_dir)

    (package_dir / "__init__.py").write_text(GENERATED_INIT_TEMPLATE, encoding="utf-8")
    _remove_toml_sections(
        project_dir / "pyproject.toml",
        section_names=("project.scripts", "tool.setuptools.package-data"),
    )
    _rewrite_generated_pyproject_description(project_dir / "pyproject.toml")


def _remove_toml_sections(pyproject_path: Path, section_names: tuple[str, ...]) -> None:
    lines = pyproject_path.read_text(encoding="utf-8").splitlines()
    updated_lines: list[str] = []
    skip_section = False

    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith("[") and stripped_line.endswith("]"):
            section_name = stripped_line.strip("[]")
            skip_section = section_name in section_names

        if not skip_section:
            updated_lines.append(line)

    pyproject_path.write_text("\n".join(updated_lines).rstrip() + "\n", encoding="utf-8")


def _rewrite_generated_pyproject_description(pyproject_path: Path) -> None:
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    pyproject_text = pyproject_text.replace(
        'description = "A minimal Python package that can reproduce itself."',
        'description = "A standalone Python package generated from a package pattern."',
    )
    pyproject_path.write_text(pyproject_text, encoding="utf-8")
