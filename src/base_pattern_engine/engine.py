"""Package instantiation implementation."""

from __future__ import annotations

import json
import keyword
import os
import re
import shutil
import stat
import uuid
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
DEFAULT_ARTIFACT_KIND = "package"
PACKAGE_ARTIFACT_KIND = "package"
SOURCE_TREE_ARTIFACT_KIND = "source-tree"
ARTIFACT_KINDS = (PACKAGE_ARTIFACT_KIND, SOURCE_TREE_ARTIFACT_KIND)
MIT_LICENSE_TYPE = "MIT"
NO_LICENSE_TYPE = "NONE"
MIT_LICENSE_CLASSIFIER = "License :: OSI Approved :: MIT License"
ROOT_FILE_NAMES = ("pyproject.toml", "LICENSE", "README.md")
MARKER_FILE_NAME = ".package-instantiation.json"
MARKER_FORMAT_VERSION = 1
UNRESOLVED_PLACEHOLDER_PREFIXES = ("<package_", "<generated_")
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
    artifact_kind: str = DEFAULT_ARTIFACT_KIND,
) -> Path:
    """Create a new standalone Python package or source tree from this installed package."""

    target = _package_identity(package_name)
    normalized_artifact_kind = _normalize_artifact_kind(artifact_kind)
    normalized_owner_name = _normalize_owner_name(owner_name)
    license_selection = _license_selection(license_type, license_text)

    source_package_dir = Path(__file__).resolve().parent
    metadata_source_dir = _metadata_source_dir(source_package_dir)
    metadata_source_paths = _metadata_source_paths(
        metadata_source_dir,
        source_package_dir,
        _root_file_names_for_artifact(normalized_artifact_kind, license_selection),
    )
    _validate_copy_sources(source_package_dir, metadata_source_paths)
    project_dir = Path(output_path).expanduser().resolve() / target.module_name
    backup_dir: Optional[Path] = None

    if project_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"Output path already exists: {project_dir}. Use overwrite=True or --overwrite to replace it."
            )
        backup_dir = _move_overwrite_target_to_backup(project_dir, target)

    src_dir = project_dir / "src"
    destination_package_dir = src_dir / target.module_name

    try:
        project_dir.mkdir(parents=True)
        src_dir.mkdir()

        _copy_project_files(metadata_source_paths, project_dir)

        shutil.copytree(
            source_package_dir,
            destination_package_dir,
            ignore=shutil.ignore_patterns(*IGNORED_COPY_PATTERNS),
        )

        _rewrite_text_files(
            project_dir,
            _text_replacements(target, license_selection, normalized_artifact_kind),
        )
        _strip_instantiation_interface(
            project_dir,
            destination_package_dir,
            normalized_owner_name,
            license_selection,
            normalized_artifact_kind,
        )
        _validate_artifact_output(project_dir, normalized_artifact_kind)
        _validate_generated_output(project_dir)
        _write_generation_marker(project_dir, target)
    except Exception:
        _restore_overwrite_backup(project_dir, backup_dir)
        raise

    if backup_dir is not None:
        _delete_overwrite_backup(backup_dir, target)

    return project_dir


def _package_identity(package_name: str) -> _PackageIdentity:
    module_name = _normalize_module_name(package_name)
    return _PackageIdentity(
        module_name=module_name,
        distribution_name=module_name.replace("_", "-"),
        title=_title_from_module_name(module_name),
    )


def _normalize_artifact_kind(artifact_kind: str) -> str:
    try:
        normalized_artifact_kind = artifact_kind.strip()
    except AttributeError as error:
        raise ValueError("Artifact kind must be a string.") from error

    if normalized_artifact_kind not in ARTIFACT_KINDS:
        allowed_values = ", ".join(ARTIFACT_KINDS)
        raise ValueError(
            f"Artifact kind must be one of: {allowed_values}. Got: {artifact_kind!r}"
        )

    return normalized_artifact_kind


def _text_replacements(
    target: _PackageIdentity,
    license_selection: _LicenseSelection,
    artifact_kind: str,
) -> dict[str, str]:
    return {
        "<package_import_name>": target.module_name,
        "<package_distribution_name>": target.distribution_name,
        "<package_title>": target.title,
        "<generated_usage_section>": _generated_usage_section(target, artifact_kind),
        "<generated_package_structure_lines>": _generated_package_structure_lines(
            target,
            license_selection,
            artifact_kind,
        ),
        "<generated_license_label>": license_selection.readme_label,
        SOURCE_MODULE_NAME: target.module_name,
        SOURCE_DISTRIBUTION_NAME: target.distribution_name,
        SOURCE_TITLE: target.title,
        SOURCE_DESCRIPTION: GENERATED_DESCRIPTION,
        "<generated_marker_file_name>": MARKER_FILE_NAME,
    }


def _generated_usage_section(target: _PackageIdentity, artifact_kind: str) -> str:
    if artifact_kind == SOURCE_TREE_ARTIFACT_KIND:
        return (
            "Add the `src` directory to `PYTHONPATH` when running Python code, or copy "
            f"`src/{target.module_name}/` into another project that manages packaging."
        )

    return "From this package directory:\n\n```shell\npython -m pip install .\n```"


def _generated_package_structure_lines(
    target: _PackageIdentity,
    license_selection: _LicenseSelection,
    artifact_kind: str,
) -> str:
    structure_lines = []
    if artifact_kind == PACKAGE_ARTIFACT_KIND:
        structure_lines.append("  pyproject.toml")
    if license_selection.include_file:
        structure_lines.append("  LICENSE")
    structure_lines.extend(
        [
            "  README.md",
            f"  {MARKER_FILE_NAME}",
            f"  src/{target.module_name}/",
        ]
    )

    return "\n".join(structure_lines)


def _metadata_source_dir(source_package_dir: Path) -> Path:
    source_project_root = _find_source_project_root(source_package_dir)
    return source_project_root or source_package_dir / "_self"


def _metadata_source_paths(
    metadata_source_dir: Path,
    source_package_dir: Path,
    root_file_names: tuple[str, ...] = ROOT_FILE_NAMES,
) -> dict[str, Path]:
    return {
        root_file_name: _project_metadata_source_path(
            metadata_source_dir,
            source_package_dir,
            root_file_name,
        )
        for root_file_name in root_file_names
    }


def _copy_project_files(metadata_source_paths: dict[str, Path], project_dir: Path) -> None:
    for root_file_name in metadata_source_paths:
        source_path = metadata_source_paths[root_file_name]
        shutil.copy2(source_path, project_dir / root_file_name)


def _root_file_names_for_artifact(
    artifact_kind: str,
    license_selection: _LicenseSelection,
) -> tuple[str, ...]:
    if artifact_kind == PACKAGE_ARTIFACT_KIND:
        return ROOT_FILE_NAMES

    if license_selection.include_file:
        return ("LICENSE", "README.md")

    return ("README.md",)


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

    pending_dirs = [path]
    while pending_dirs:
        current_dir = pending_dirs.pop()
        for candidate_path in current_dir.iterdir():
            if _is_filesystem_link(candidate_path):
                raise ValueError(f"Refusing to copy symlink or junction: {candidate_path}")
            if candidate_path.is_dir():
                pending_dirs.append(candidate_path)


def _is_filesystem_link(path: Path) -> bool:
    if path.is_symlink():
        return True

    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction and is_junction()) or _is_windows_reparse_point(path)


def _is_windows_reparse_point(path: Path) -> bool:
    if os.name != "nt":
        return False

    try:
        file_attributes = path.lstat().st_file_attributes
    except (AttributeError, OSError):
        return False

    reparse_point_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(file_attributes & reparse_point_attribute)


def _move_overwrite_target_to_backup(project_dir: Path, target: _PackageIdentity) -> Path:
    _validate_overwrite_target(project_dir, target)
    backup_dir = _unused_overwrite_backup_path(project_dir)
    project_dir.rename(backup_dir)

    try:
        _validate_overwrite_target(backup_dir, target)
    except Exception:
        if not project_dir.exists():
            backup_dir.rename(project_dir)
        raise

    return backup_dir


def _unused_overwrite_backup_path(project_dir: Path) -> Path:
    for _ in range(100):
        backup_dir = project_dir.with_name(
            f".{project_dir.name}.overwrite-backup-{uuid.uuid4().hex}"
        )
        if not backup_dir.exists():
            return backup_dir

    raise FileExistsError(f"Cannot allocate overwrite backup path for: {project_dir}")


def _restore_overwrite_backup(project_dir: Path, backup_dir: Optional[Path]) -> None:
    if backup_dir is None or not backup_dir.exists():
        return

    if project_dir.exists():
        _delete_unmarked_project_tree(project_dir)

    backup_dir.rename(project_dir)


def _delete_overwrite_backup(backup_dir: Path, target: _PackageIdentity) -> None:
    _validate_overwrite_target(backup_dir, target)
    shutil.rmtree(backup_dir)


def _delete_unmarked_project_tree(project_dir: Path) -> None:
    if _is_filesystem_link(project_dir) or not project_dir.is_dir():
        raise FileExistsError(f"Output path exists and is not a regular directory: {project_dir}")

    try:
        _reject_filesystem_links(project_dir)
    except ValueError as error:
        raise FileExistsError(
            f"Refusing to remove directory containing symlink or junction: {project_dir}"
        ) from error

    shutil.rmtree(project_dir)


def _validate_overwrite_target(project_dir: Path, target: _PackageIdentity) -> None:
    if _is_filesystem_link(project_dir) or not project_dir.is_dir():
        raise FileExistsError(f"Output path exists and is not a regular directory: {project_dir}")

    try:
        _reject_filesystem_links(project_dir)
    except ValueError as error:
        raise FileExistsError(
            f"Refusing to overwrite directory containing symlink or junction: {project_dir}"
        ) from error

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
    if _contains_control_character(normalized_owner_name):
        raise ValueError("Owner name cannot contain control characters.")

    return normalized_owner_name


def _license_selection(license_type: str, license_text: Optional[str]) -> _LicenseSelection:
    normalized_license_type = license_type.strip()

    if not normalized_license_type:
        raise ValueError("License cannot be empty. Use 'NONE' to omit generated license metadata.")
    if _contains_control_character(normalized_license_type):
        raise ValueError("License cannot contain control characters.")

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
    if _contains_disallowed_license_text_control_character(normalized_license_text):
        raise ValueError(
            "License text cannot contain control characters other than tabs or newlines."
        )
    if not normalized_license_text.endswith("\n"):
        normalized_license_text += "\n"

    return normalized_license_text


def _contains_control_character(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _contains_disallowed_license_text_control_character(value: str) -> bool:
    return any(
        (ord(character) < 32 and character not in "\n\t") or ord(character) == 127
        for character in value
    )


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


def _validate_generated_output(project_dir: Path) -> None:
    unresolved_files = []

    for file_path in project_dir.rglob("*"):
        if not file_path.is_file():
            continue

        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if any(prefix in text for prefix in UNRESOLVED_PLACEHOLDER_PREFIXES):
            unresolved_files.append(file_path.relative_to(project_dir))

    if unresolved_files:
        unresolved_list = ", ".join(str(file_path) for file_path in unresolved_files)
        raise ValueError(
            f"Generated output contains unresolved template placeholders: {unresolved_list}"
        )


def _strip_instantiation_interface(
    project_dir: Path,
    package_dir: Path,
    owner_name: str,
    license_selection: _LicenseSelection,
    artifact_kind: str,
) -> None:
    for relative_path in ("engine.py", "cli.py"):
        file_path = package_dir / relative_path
        if file_path.exists():
            file_path.unlink()

    bundled_metadata_dir = package_dir / "_self"
    if bundled_metadata_dir.exists():
        shutil.rmtree(bundled_metadata_dir)

    (package_dir / "__init__.py").write_text(GENERATED_INIT_TEMPLATE, encoding="utf-8")
    if artifact_kind == PACKAGE_ARTIFACT_KIND:
        _transform_generated_pyproject(
            project_dir / "pyproject.toml",
            owner_name,
            license_selection,
        )
    _apply_generated_license(project_dir / "LICENSE", owner_name, license_selection)


def _validate_artifact_output(project_dir: Path, artifact_kind: str) -> None:
    if artifact_kind != SOURCE_TREE_ARTIFACT_KIND:
        return

    package_metadata_files = ("pyproject.toml", "setup.py", "setup.cfg", "MANIFEST.in")
    unexpected_files = [
        file_name for file_name in package_metadata_files if (project_dir / file_name).exists()
    ]
    if unexpected_files:
        unexpected_list = ", ".join(unexpected_files)
        raise ValueError(f"Source-tree output contains package build metadata: {unexpected_list}")


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
        raise ValueError("Cannot locate copyright notice in generated MIT license text.")

    license_path.write_text(updated_text, encoding="utf-8")
