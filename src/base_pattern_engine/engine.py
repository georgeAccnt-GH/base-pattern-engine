"""Package instantiation implementation."""

from __future__ import annotations

import json
import keyword
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import tomlkit

SOURCE_MODULE_NAME = "base_pattern_engine"
SOURCE_DISTRIBUTION_NAME = "base-pattern-engine"
SOURCE_TITLE = "Base Pattern Engine"
SOURCE_DESCRIPTION = "A minimal Python package instantiation engine."
GENERATED_DESCRIPTION = "A standalone Python package generated from a package instantiation pattern."
DEFAULT_OWNER_NAME = "Package contributors"
DEFAULT_LICENSE_TYPE = "MIT"
MIT_LICENSE_TYPE = "MIT"
NO_LICENSE_TYPE = "NONE"
MIT_LICENSE_CLASSIFIER = "License :: OSI Approved :: MIT License"
ROOT_FILE_NAMES = ("pyproject.toml", "LICENSE", "README.md")
MARKER_FILE_NAME = ".package-instantiation.json"
MARKER_FORMAT_VERSION = 1
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


@dataclass(frozen=True)
class _PackageIdentity:
    module_name: str
    distribution_name: str
    title: str


@dataclass(frozen=True)
class _LicenseSelection:
    expression: Optional[str]
    text: Optional[str]
    include_file: bool
    readme_label: str


def instantiate(
    package_name: str,
    output_path: str = ".",
    license_type: str = DEFAULT_LICENSE_TYPE,
    overwrite: bool = False,
    owner_name: str = DEFAULT_OWNER_NAME,
    license_text: Optional[str] = None,
) -> Path:
    """Create a new standalone Python package from this installed package."""

    target = _package_identity(package_name)
    normalized_owner_name = _normalize_owner_name(owner_name)
    license_selection = _license_selection(license_type, license_text)

    source_package_dir = Path(__file__).resolve().parent
    metadata_source_dir = _metadata_source_dir(source_package_dir)
    metadata_source_paths = _metadata_source_paths(metadata_source_dir, source_package_dir)
    _validate_copy_sources(source_package_dir, metadata_source_paths)
    project_dir = Path(output_path).expanduser().resolve() / target.module_name

    if project_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"Output path already exists: {project_dir}. Use overwrite=True or --overwrite to replace it."
            )
        _validate_overwrite_target(project_dir, target)
        shutil.rmtree(project_dir)

    src_dir = project_dir / "src"
    destination_package_dir = src_dir / target.module_name

    project_dir.mkdir(parents=True)
    src_dir.mkdir()

    _copy_project_files(metadata_source_paths, project_dir)

    shutil.copytree(
        source_package_dir,
        destination_package_dir,
        ignore=shutil.ignore_patterns(*IGNORED_COPY_PATTERNS),
    )

    _rewrite_text_files(project_dir, _text_replacements(target, license_selection))
    _strip_instantiation_interface(
        project_dir,
        destination_package_dir,
        normalized_owner_name,
        license_selection,
    )
    _write_generation_marker(project_dir, target)

    return project_dir


def _package_identity(package_name: str) -> _PackageIdentity:
    module_name = _normalize_module_name(package_name)
    return _PackageIdentity(
        module_name=module_name,
        distribution_name=module_name.replace("_", "-"),
        title=_title_from_module_name(module_name),
    )


def _text_replacements(target: _PackageIdentity, license_selection: _LicenseSelection) -> dict[str, str]:
    return {
        "<package_import_name>": target.module_name,
        "<package_distribution_name>": target.distribution_name,
        "<package_title>": target.title,
        "<generated_license_and_readme_file_lines>": _license_and_readme_file_lines(
            license_selection
        ),
        "<generated_license_label>": license_selection.readme_label,
        SOURCE_MODULE_NAME: target.module_name,
        SOURCE_DISTRIBUTION_NAME: target.distribution_name,
        SOURCE_TITLE: target.title,
        SOURCE_DESCRIPTION: GENERATED_DESCRIPTION,
        "<generated_marker_file_name>": MARKER_FILE_NAME,
    }


def _license_and_readme_file_lines(license_selection: _LicenseSelection) -> str:
    if license_selection.include_file:
        return "  LICENSE\n  README.md"

    return "  README.md"


def _metadata_source_dir(source_package_dir: Path) -> Path:
    source_project_root = _find_source_project_root(source_package_dir)
    return source_project_root or source_package_dir / "_self"


def _metadata_source_paths(metadata_source_dir: Path, source_package_dir: Path) -> dict[str, Path]:
    return {
        root_file_name: _project_metadata_source_path(
            metadata_source_dir,
            source_package_dir,
            root_file_name,
        )
        for root_file_name in ROOT_FILE_NAMES
    }


def _copy_project_files(metadata_source_paths: dict[str, Path], project_dir: Path) -> None:
    for root_file_name in ROOT_FILE_NAMES:
        source_path = metadata_source_paths[root_file_name]
        shutil.copy2(source_path, project_dir / root_file_name)


def _validate_copy_sources(source_package_dir: Path, metadata_source_paths: dict[str, Path]) -> None:
    _reject_filesystem_links(source_package_dir)

    missing_files = [
        root_file_name
        for root_file_name, source_path in metadata_source_paths.items()
        if not source_path.is_file()
    ]
    if missing_files:
        missing_list = ", ".join(missing_files)
        raise ValueError(f"Cannot locate package metadata files: {missing_list}")

    for source_path in metadata_source_paths.values():
        _reject_filesystem_links(source_path)


def _project_metadata_source_path(
    metadata_source_dir: Path,
    source_package_dir: Path,
    root_file_name: str,
) -> Path:
    if root_file_name == "README.md":
        return source_package_dir / "_self" / "README.md"

    return metadata_source_dir / root_file_name


def _reject_filesystem_links(path: Path) -> None:
    if _is_filesystem_link(path):
        raise ValueError(f"Refusing to copy symlink or junction: {path}")

    if not path.is_dir():
        return

    for candidate_path in path.rglob("*"):
        if _is_filesystem_link(candidate_path):
            raise ValueError(f"Refusing to copy symlink or junction: {candidate_path}")


def _is_filesystem_link(path: Path) -> bool:
    if path.is_symlink():
        return True

    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction and is_junction())


def _validate_overwrite_target(project_dir: Path, target: _PackageIdentity) -> None:
    if _is_filesystem_link(project_dir) or not project_dir.is_dir():
        raise FileExistsError(f"Output path exists and is not a regular directory: {project_dir}")

    marker_path = project_dir / MARKER_FILE_NAME
    if _is_filesystem_link(marker_path) or not marker_path.is_file():
        raise FileExistsError(
            f"Refusing to overwrite unmarked directory: {project_dir}. Expected marker file {MARKER_FILE_NAME}."
        )

    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FileExistsError(f"Refusing to overwrite directory with invalid marker: {marker_path}") from error

    expected_marker = _generation_marker(target)
    if marker != expected_marker:
        raise FileExistsError(
            f"Refusing to overwrite directory with marker that does not match package '{target.module_name}': {project_dir}"
        )


def _write_generation_marker(project_dir: Path, target: _PackageIdentity) -> None:
    marker = _generation_marker(target)
    marker_text = json.dumps(marker, indent=2, sort_keys=True) + "\n"
    (project_dir / MARKER_FILE_NAME).write_text(marker_text, encoding="utf-8")


def _generation_marker(target: _PackageIdentity) -> dict[str, Union[int, str]]:
    return {
        "format_version": MARKER_FORMAT_VERSION,
        "module_name": target.module_name,
        "distribution_name": target.distribution_name,
    }


def _find_source_project_root(source_package_dir: Path) -> Optional[Path]:
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


def _normalize_owner_name(owner_name: str) -> str:
    normalized_owner_name = owner_name.strip()

    if not normalized_owner_name:
        raise ValueError("Owner name cannot be empty.")
    if "\n" in normalized_owner_name or "\r" in normalized_owner_name:
        raise ValueError("Owner name cannot contain line breaks.")

    return normalized_owner_name


def _license_selection(license_type: str, license_text: Optional[str]) -> _LicenseSelection:
    normalized_license_type = license_type.strip()

    if not normalized_license_type:
        raise ValueError("License cannot be empty. Use 'NONE' to omit generated license metadata.")
    if "\n" in normalized_license_type or "\r" in normalized_license_type:
        raise ValueError("License cannot contain line breaks.")

    normalized_license_text = _normalize_license_text(license_text)
    upper_license_type = normalized_license_type.upper()

    if upper_license_type == NO_LICENSE_TYPE:
        if normalized_license_text is not None:
            raise ValueError("License text cannot be used when license is NONE.")

        return _LicenseSelection(
            expression=None,
            text=None,
            include_file=False,
            readme_label="Not specified",
        )

    return _LicenseSelection(
        expression=MIT_LICENSE_TYPE if upper_license_type == MIT_LICENSE_TYPE else normalized_license_type,
        text=normalized_license_text,
        include_file=upper_license_type == MIT_LICENSE_TYPE or normalized_license_text is not None,
        readme_label=MIT_LICENSE_TYPE if upper_license_type == MIT_LICENSE_TYPE else normalized_license_type,
    )


def _normalize_license_text(license_text: Optional[str]) -> Optional[str]:
    if license_text is None:
        return None

    normalized_license_text = license_text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized_license_text.strip():
        raise ValueError("License text cannot be empty.")
    if not normalized_license_text.endswith("\n"):
        normalized_license_text += "\n"

    return normalized_license_text


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


def _strip_instantiation_interface(
    project_dir: Path,
    package_dir: Path,
    owner_name: str,
    license_selection: _LicenseSelection,
) -> None:
    for relative_path in ("engine.py", "cli.py"):
        file_path = package_dir / relative_path
        if file_path.exists():
            file_path.unlink()

    bundled_metadata_dir = package_dir / "_self"
    if bundled_metadata_dir.exists():
        shutil.rmtree(bundled_metadata_dir)

    (package_dir / "__init__.py").write_text(GENERATED_INIT_TEMPLATE, encoding="utf-8")
    _transform_generated_pyproject(project_dir / "pyproject.toml", owner_name, license_selection)
    _apply_generated_license(project_dir / "LICENSE", owner_name, license_selection)


def _transform_generated_pyproject(
    pyproject_path: Path,
    owner_name: str,
    license_selection: _LicenseSelection,
) -> None:
    document = tomlkit.parse(pyproject_path.read_text(encoding="utf-8"))
    project_table = document["project"]
    project_table["description"] = GENERATED_DESCRIPTION
    project_table["authors"] = [{"name": owner_name}]
    _transform_generated_pyproject_license(project_table, license_selection)
    project_table.pop("dependencies", None)
    project_table.pop("optional-dependencies", None)
    project_table.pop("scripts", None)

    tool_table = document.get("tool")
    if tool_table is not None:
        setuptools_table = tool_table.get("setuptools")
        if setuptools_table is not None:
            setuptools_table.pop("package-data", None)

    pyproject_path.write_text(tomlkit.dumps(document), encoding="utf-8")


def _transform_generated_pyproject_license(
    project_table: tomlkit.items.Table,
    license_selection: _LicenseSelection,
) -> None:
    classifiers = project_table.get("classifiers", [])
    project_table["classifiers"] = [
        classifier
        for classifier in classifiers
        if classifier != MIT_LICENSE_CLASSIFIER or license_selection.expression == MIT_LICENSE_TYPE
    ]

    if license_selection.expression is None:
        project_table.pop("license", None)
    elif license_selection.include_file:
        project_table["license"] = {"file": "LICENSE"}
    else:
        project_table["license"] = {"text": license_selection.expression}


def _apply_generated_license(
    license_path: Path,
    owner_name: str,
    license_selection: _LicenseSelection,
) -> None:
    if not license_selection.include_file:
        if license_path.exists():
            license_path.unlink()
        return

    if license_selection.text is not None:
        license_path.write_text(license_selection.text, encoding="utf-8")
        return

    _rewrite_generated_license(license_path, owner_name)


def _rewrite_generated_license(license_path: Path, owner_name: str) -> None:
    license_text = license_path.read_text(encoding="utf-8")
    updated_text, substitution_count = re.subn(
        r"Copyright \(c\) (\d{4}) .+",
        lambda match: f"Copyright (c) {match.group(1)} {owner_name}",
        license_text,
        count=1,
    )
    if substitution_count != 1:
        raise ValueError(f"Cannot locate copyright notice in license file: {license_path}")

    license_path.write_text(updated_text, encoding="utf-8")
