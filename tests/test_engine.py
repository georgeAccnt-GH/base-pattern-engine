from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest
import tomlkit

import base_pattern_engine
import base_pattern_engine.engine as engine_module
from base_pattern_engine import (
    DISTRIBUTION_NAME,
    MODULE_NAME,
    instantiate,
    print_package_identity,
)
from base_pattern_engine.engine import (
    MARKER_FILE_NAME,
    MARKER_FORMAT_VERSION,
    _is_filesystem_link,
    _metadata_source_paths,
    _reject_filesystem_links,
    _rewrite_generated_license,
    _validate_copy_sources,
    _validate_generated_output,
)


def _parse_toml(text: str) -> Any:
    return cast(Any, tomlkit.parse(text))


def test_instantiate_creates_standalone_package(tmp_path: Path) -> None:
    created_path = instantiate("my_package", output_path=str(tmp_path), license_type="MIT")

    assert created_path == tmp_path / "my_package"
    assert (created_path / "pyproject.toml").is_file()
    assert (created_path / "LICENSE").is_file()
    assert (created_path / "README.md").is_file()
    assert (created_path / MARKER_FILE_NAME).is_file()
    assert (created_path / "src" / "my_package" / "__init__.py").is_file()
    assert (created_path / "src" / "my_package" / "core.py").is_file()


def test_instantiate_accepts_explicit_package_artifact_kind(tmp_path: Path) -> None:
    created_path = instantiate(
        "my_package",
        output_path=str(tmp_path),
        artifact_kind="package",
    )

    assert (created_path / "pyproject.toml").is_file()
    assert (created_path / "src" / "my_package" / "core.py").is_file()


def test_instantiate_creates_source_tree_artifact(tmp_path: Path) -> None:
    created_path = instantiate(
        "my_code",
        output_path=str(tmp_path),
        artifact_kind="source-tree",
    )
    package_path = created_path / "src" / "my_code"
    readme_text = (created_path / "README.md").read_text(encoding="utf-8")
    all_text = "\n".join(
        file_path.read_text(encoding="utf-8")
        for file_path in created_path.rglob("*")
        if file_path.is_file()
    )

    assert created_path == tmp_path / "my_code"
    assert not (created_path / "pyproject.toml").exists()
    assert (created_path / "LICENSE").is_file()
    assert (created_path / "README.md").is_file()
    assert (created_path / MARKER_FILE_NAME).is_file()
    assert (package_path / "__init__.py").is_file()
    assert (package_path / "core.py").is_file()
    assert not (package_path / "engine.py").exists()
    assert not (package_path / "cli.py").exists()
    assert not (package_path / "_self").exists()
    assert "python -m pip install ." not in readme_text
    assert "PYTHONPATH" in readme_text
    assert "src/my_code/" in readme_text
    assert "pyproject.toml" not in readme_text
    assert "base_pattern_engine" not in all_text
    assert "base-pattern-engine" not in all_text
    assert "Base Pattern Engine" not in all_text
    assert "<package_" not in all_text
    assert "<generated_" not in all_text


def test_instantiate_writes_matching_generation_marker(tmp_path: Path) -> None:
    created_path = instantiate("my_package", output_path=str(tmp_path))

    marker = json.loads((created_path / MARKER_FILE_NAME).read_text(encoding="utf-8"))

    assert marker == {
        "distribution_name": "my-package",
        "format_version": MARKER_FORMAT_VERSION,
        "module_name": "my_package",
    }


def test_packaged_fallback_metadata_has_no_source_identity() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    fallback_metadata_dir = repository_root / "src" / "base_pattern_engine" / "_self"
    fallback_pyproject_text = (fallback_metadata_dir / "pyproject.toml").read_text(encoding="utf-8")
    fallback_license_text = (fallback_metadata_dir / "LICENSE").read_text(encoding="utf-8")
    fallback_pyproject = _parse_toml(fallback_pyproject_text)

    assert fallback_pyproject["project"]["name"] == "<package_distribution_name>"
    assert (
        fallback_pyproject["project"]["description"]
        == "A standalone Python package generated from a package instantiation pattern."
    )
    assert fallback_pyproject["project"]["authors"] == [{"name": "Package contributors"}]
    assert fallback_pyproject["project"]["license"] == {"file": "LICENSE"}
    assert "dependencies" not in fallback_pyproject["project"]
    assert "optional-dependencies" not in fallback_pyproject["project"]
    assert "scripts" not in fallback_pyproject["project"]
    assert "package-data" not in fallback_pyproject["tool"]["setuptools"]
    assert "Copyright (c) 2026 Package contributors" in fallback_license_text
    assert "base-pattern-engine" not in fallback_pyproject_text
    assert "base_pattern_engine" not in fallback_pyproject_text
    assert "Base Pattern Engine" not in fallback_pyproject_text
    assert "George Iordanescu" not in fallback_pyproject_text
    assert "George Iordanescu" not in fallback_license_text


def test_instantiate_from_packaged_fallback_has_no_source_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    installed_package_dir = tmp_path / "site-packages" / "base_pattern_engine"
    shutil.copytree(repository_root / "src" / "base_pattern_engine", installed_package_dir)
    monkeypatch.setattr(engine_module, "__file__", str(installed_package_dir / "engine.py"))

    created_path = engine_module.instantiate("fallback_package", output_path=str(tmp_path / "out"))
    all_text = "\n".join(
        file_path.read_text(encoding="utf-8")
        for file_path in created_path.rglob("*")
        if file_path.is_file()
    )

    pyproject = _parse_toml((created_path / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["name"] == "fallback-package"
    assert pyproject["project"]["authors"] == [{"name": "Package contributors"}]
    assert "<package_" not in all_text
    assert "base-pattern-engine" not in all_text
    assert "base_pattern_engine" not in all_text
    assert "Base Pattern Engine" not in all_text
    assert "George Iordanescu" not in all_text


def test_metadata_validation_requires_generated_readme_template(tmp_path: Path) -> None:
    source_package_dir = tmp_path / "src" / "base_pattern_engine"
    source_package_dir.mkdir(parents=True)
    metadata_source_dir = tmp_path
    (metadata_source_dir / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (metadata_source_dir / "LICENSE").write_text("MIT\n", encoding="utf-8")

    metadata_source_paths = _metadata_source_paths(metadata_source_dir, source_package_dir)

    with pytest.raises(ValueError, match="README.md"):
        _validate_copy_sources(source_package_dir, metadata_source_paths)


def test_instantiate_rewrites_package_identity(tmp_path: Path) -> None:
    created_path = instantiate("my_package", output_path=str(tmp_path))

    all_text = "\n".join(
        file_path.read_text(encoding="utf-8")
        for file_path in created_path.rglob("*")
        if file_path.is_file()
    )

    assert "base_pattern_engine" not in all_text
    assert "base-pattern-engine" not in all_text
    assert "Base Pattern Engine" not in all_text
    assert "George Iordanescu" not in all_text
    assert "<package_" not in all_text
    assert "<generated_" not in all_text
    assert "Package contributors" in all_text
    assert "my_package" in all_text
    assert "my-package" in all_text


def test_identity_function_prints_instantiated_package_identity(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    created_path = instantiate("my_package", output_path=str(tmp_path))
    generated_src_path = str(created_path / "src")

    print_package_identity()
    source_output = capsys.readouterr().out

    assert MODULE_NAME == "base_pattern_engine"
    assert DISTRIBUTION_NAME == "base-pattern-engine"
    assert not hasattr(base_pattern_engine, "PACKAGE_NAME")
    assert not hasattr(base_pattern_engine, "print_package_name")

    sys.path.insert(0, generated_src_path)
    try:
        generated_package = importlib.import_module("my_package")
        generated_package.print_package_identity()
        generated_output = capsys.readouterr().out
        assert generated_package.MODULE_NAME == "my_package"
        assert generated_package.DISTRIBUTION_NAME == "my-package"
        assert not hasattr(generated_package, "PACKAGE_NAME")
        assert not hasattr(generated_package, "print_package_name")
        assert not hasattr(generated_package, "instantiate")
    finally:
        sys.path.remove(generated_src_path)
        sys.modules.pop("my_package", None)

    assert source_output == "module: base_pattern_engine\ndistribution: base-pattern-engine\n"
    assert generated_output == "module: my_package\ndistribution: my-package\n"


def test_generated_package_can_be_pip_installed_independently(tmp_path: Path) -> None:
    created_path = instantiate("my_package", output_path=str(tmp_path))
    install_path = tmp_path / "install"
    install_env = os.environ.copy()
    install_env.pop("PYTHONPATH", None)

    install_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-build-isolation",
            "--no-deps",
            "--target",
            str(install_path),
            str(created_path),
        ],
        cwd=tmp_path,
        env=install_env,
        capture_output=True,
        text=True,
    )
    assert install_result.returncode == 0, install_result.stderr

    run_env = install_env.copy()
    run_env["PYTHONPATH"] = str(install_path)
    import_result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "import importlib.util, my_package; "
            "assert my_package.MODULE_NAME == 'my_package'; "
            "assert my_package.DISTRIBUTION_NAME == 'my-package'; "
            "assert not hasattr(my_package, 'PACKAGE_NAME'); "
            "assert not hasattr(my_package, 'print_package_name'); "
            "assert not hasattr(my_package, 'instantiate'); "
            "assert importlib.util.find_spec('base_pattern_engine') is None; "
            "assert importlib.util.find_spec('my_package.engine') is None; "
            "assert importlib.util.find_spec('my_package.cli') is None; "
            "my_package.print_package_identity()",
        ],
        cwd=tmp_path,
        env=run_env,
        capture_output=True,
        text=True,
    )
    assert import_result.returncode == 0, import_result.stderr
    assert import_result.stdout == "module: my_package\ndistribution: my-package\n"


def test_generated_source_tree_can_be_imported_independently(tmp_path: Path) -> None:
    created_path = instantiate(
        "my_code",
        output_path=str(tmp_path),
        artifact_kind="source-tree",
    )
    run_env = os.environ.copy()
    run_env.pop("PYTHONPATH", None)
    run_env["PYTHONPATH"] = str(created_path / "src")

    import_result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "import importlib.util, my_code; "
            "assert my_code.MODULE_NAME == 'my_code'; "
            "assert my_code.DISTRIBUTION_NAME == 'my-code'; "
            "assert not hasattr(my_code, 'PACKAGE_NAME'); "
            "assert not hasattr(my_code, 'print_package_name'); "
            "assert not hasattr(my_code, 'instantiate'); "
            "assert importlib.util.find_spec('base_pattern_engine') is None; "
            "assert importlib.util.find_spec('my_code.engine') is None; "
            "assert importlib.util.find_spec('my_code.cli') is None; "
            "my_code.print_package_identity()",
        ],
        cwd=tmp_path,
        env=run_env,
        capture_output=True,
        text=True,
    )

    assert import_result.returncode == 0, import_result.stderr
    assert import_result.stdout == "module: my_code\ndistribution: my-code\n"


def test_instantiated_package_has_no_instantiation_interface(tmp_path: Path) -> None:
    created_path = instantiate("my_package", output_path=str(tmp_path))
    package_path = created_path / "src" / "my_package"
    pyproject_text = (created_path / "pyproject.toml").read_text(encoding="utf-8")
    readme_text = (created_path / "README.md").read_text(encoding="utf-8")

    assert not (package_path / "engine.py").exists()
    assert not (package_path / "cli.py").exists()
    assert not (package_path / "_self").exists()
    assert "[project.scripts]" not in pyproject_text
    assert "dependencies" not in pyproject_text
    assert "[project.optional-dependencies]" not in pyproject_text
    assert "[tool.setuptools.package-data]" not in pyproject_text
    assert (
        'description = "A standalone Python package generated from a package instantiation pattern."'
        in pyproject_text
    )
    assert "A minimal Python package instantiation engine." not in pyproject_text
    assert "instantiate" not in (package_path / "__init__.py").read_text(encoding="utf-8")
    assert "<package_" not in readme_text
    assert "<generated_" not in readme_text
    assert "# My Package" in readme_text
    assert "from my_package import DISTRIBUTION_NAME, MODULE_NAME, print_package_identity" in readme_text
    assert "PACKAGE_NAME" not in readme_text
    assert "print_package_name" not in readme_text
    assert MARKER_FILE_NAME in readme_text
    assert "my-package/" in readme_text


def test_instantiated_pyproject_is_standalone_metadata(tmp_path: Path) -> None:
    created_path = instantiate("my_package", output_path=str(tmp_path))

    pyproject = _parse_toml((created_path / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["name"] == "my-package"
    assert (
        pyproject["project"]["description"]
        == "A standalone Python package generated from a package instantiation pattern."
    )
    assert pyproject["project"]["authors"] == [{"name": "Package contributors"}]
    assert pyproject["project"]["license"] == {"file": "LICENSE"}
    assert "dependencies" not in pyproject["project"]
    assert "optional-dependencies" not in pyproject["project"]
    assert "scripts" not in pyproject["project"]
    assert pyproject["tool"]["setuptools"]["packages"]["find"]["where"] == ["src"]
    assert "package-data" not in pyproject["tool"]["setuptools"]


def test_instantiate_rejects_existing_output_without_overwrite(tmp_path: Path) -> None:
    instantiate("my_package", output_path=str(tmp_path))

    with pytest.raises(FileExistsError, match="--overwrite"):
        instantiate("my_package", output_path=str(tmp_path))


def test_instantiate_overwrites_existing_output(tmp_path: Path) -> None:
    created_path = instantiate("my_package", output_path=str(tmp_path))
    stale_file = created_path / "stale.txt"
    stale_file.write_text("old content", encoding="utf-8")

    overwritten_path = instantiate("my_package", output_path=str(tmp_path), overwrite=True)

    assert overwritten_path == created_path
    assert not stale_file.exists()
    assert (overwritten_path / "src" / "my_package" / "core.py").is_file()


def test_instantiate_overwrites_existing_source_tree_output(tmp_path: Path) -> None:
    created_path = instantiate(
        "my_code",
        output_path=str(tmp_path),
        artifact_kind="source-tree",
    )
    stale_file = created_path / "stale.txt"
    stale_file.write_text("old content", encoding="utf-8")

    overwritten_path = instantiate(
        "my_code",
        output_path=str(tmp_path),
        overwrite=True,
        artifact_kind="source-tree",
    )

    assert overwritten_path == created_path
    assert not stale_file.exists()
    assert not (overwritten_path / "pyproject.toml").exists()
    assert (overwritten_path / "src" / "my_code" / "core.py").is_file()


def test_instantiate_restores_existing_output_when_overwrite_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    created_path = instantiate("my_package", output_path=str(tmp_path))
    preserved_file = created_path / "preserved.txt"
    preserved_file.write_text("original content", encoding="utf-8")

    def fail_generated_output_validation(project_dir: Path) -> None:
        raise ValueError("forced generated output validation failure")

    monkeypatch.setattr(
        engine_module,
        "_validate_generated_output",
        fail_generated_output_validation,
    )

    with pytest.raises(ValueError, match="forced generated output validation failure"):
        engine_module.instantiate("my_package", output_path=str(tmp_path), overwrite=True)

    assert preserved_file.read_text(encoding="utf-8") == "original content"
    assert not list(tmp_path.glob(".my_package.overwrite-backup-*"))


def test_instantiate_accepts_all_arguments_when_overwriting(tmp_path: Path) -> None:
    created_path = instantiate("all_arguments", output_path=str(tmp_path))
    stale_file = created_path / "stale.txt"
    stale_file.write_text("old content", encoding="utf-8")

    overwritten_path = instantiate(
        package_name="all_arguments",
        output_path=str(tmp_path),
        license_type="MIT",
        overwrite=True,
        owner_name="Example Package Team",
        license_text=None,
    )

    assert overwritten_path == created_path
    assert not stale_file.exists()
    assert "Example Package Team" in (overwritten_path / "LICENSE").read_text(encoding="utf-8")


def test_instantiate_uses_custom_generated_owner(tmp_path: Path) -> None:
    created_path = instantiate(
        "owned_package",
        output_path=str(tmp_path),
        owner_name="Example Organization",
    )

    pyproject = _parse_toml((created_path / "pyproject.toml").read_text(encoding="utf-8"))
    license_text = (created_path / "LICENSE").read_text(encoding="utf-8")

    assert pyproject["project"]["authors"] == [{"name": "Example Organization"}]
    assert "Copyright (c) 2026 Example Organization" in license_text
    assert "George Iordanescu" not in license_text


def test_instantiate_can_omit_generated_license(tmp_path: Path) -> None:
    created_path = instantiate("unlicensed_package", output_path=str(tmp_path), license_type="NONE")

    pyproject = _parse_toml((created_path / "pyproject.toml").read_text(encoding="utf-8"))
    readme_text = (created_path / "README.md").read_text(encoding="utf-8")

    assert not (created_path / "LICENSE").exists()
    assert "license" not in pyproject["project"]
    assert "License :: OSI Approved :: MIT License" not in pyproject["project"]["classifiers"]
    assert "Not specified" in readme_text
    assert "<generated_" not in readme_text
    assert "  LICENSE" not in readme_text


def test_instantiate_uses_custom_license_expression_without_file(tmp_path: Path) -> None:
    created_path = instantiate(
        "apache_package",
        output_path=str(tmp_path),
        license_type="Apache-2.0",
    )

    pyproject = _parse_toml((created_path / "pyproject.toml").read_text(encoding="utf-8"))
    readme_text = (created_path / "README.md").read_text(encoding="utf-8")

    assert not (created_path / "LICENSE").exists()
    assert pyproject["project"]["license"] == {"text": "Apache-2.0"}
    assert "License :: OSI Approved :: MIT License" not in pyproject["project"]["classifiers"]
    assert "Apache-2.0" in readme_text
    assert "<generated_" not in readme_text
    assert "  LICENSE" not in readme_text


def test_source_tree_custom_license_expression_has_no_package_metadata(tmp_path: Path) -> None:
    created_path = instantiate(
        "source_license",
        output_path=str(tmp_path),
        artifact_kind="source-tree",
        license_type="Apache-2.0",
    )
    readme_text = (created_path / "README.md").read_text(encoding="utf-8")

    assert not (created_path / "pyproject.toml").exists()
    assert not (created_path / "LICENSE").exists()
    assert "Apache-2.0" in readme_text
    assert "  LICENSE" not in readme_text


def test_source_tree_custom_license_text_writes_license_without_package_metadata(
    tmp_path: Path,
) -> None:
    created_path = instantiate(
        "source_custom_license",
        output_path=str(tmp_path),
        artifact_kind="source-tree",
        license_type="Example-License",
        license_text="Example source-tree license text",
    )
    readme_text = (created_path / "README.md").read_text(encoding="utf-8")

    assert not (created_path / "pyproject.toml").exists()
    assert (created_path / "LICENSE").read_text(encoding="utf-8") == (
        "Example source-tree license text\n"
    )
    assert "Example-License" in readme_text
    assert "  LICENSE" in readme_text


def test_instantiate_uses_custom_license_text(tmp_path: Path) -> None:
    created_path = instantiate(
        "custom_license_package",
        output_path=str(tmp_path),
        license_type="Example-License",
        license_text="Example custom license text",
    )

    pyproject = _parse_toml((created_path / "pyproject.toml").read_text(encoding="utf-8"))
    license_text = (created_path / "LICENSE").read_text(encoding="utf-8")
    readme_text = (created_path / "README.md").read_text(encoding="utf-8")

    assert pyproject["project"]["license"] == {"file": "LICENSE"}
    assert "License :: OSI Approved :: MIT License" not in pyproject["project"]["classifiers"]
    assert license_text == "Example custom license text\n"
    assert "Example-License" in readme_text
    assert "<generated_" not in readme_text
    assert "  LICENSE" in readme_text


def test_generated_license_rewrite_requires_copyright_notice(tmp_path: Path) -> None:
    license_path = tmp_path / "LICENSE"
    license_path.write_text("MIT License\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Cannot locate copyright notice"):
        _rewrite_generated_license(license_path, "Example Organization")

    assert license_path.read_text(encoding="utf-8") == "MIT License\n"


def test_generated_output_validation_rejects_unresolved_placeholders(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "README.md").write_text("# <package_title>\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unresolved template placeholders"):
        _validate_generated_output(project_dir)


@pytest.mark.parametrize("owner_name", ["", "  ", "Package\ncontributors", "Package\tcontributors"])
def test_instantiate_rejects_invalid_owner_name(tmp_path: Path, owner_name: str) -> None:
    with pytest.raises(ValueError, match="Owner name"):
        instantiate("my_package", output_path=str(tmp_path), owner_name=owner_name)


@pytest.mark.parametrize("license_type", ["", "  ", "MIT\nApache-2.0", "MIT\tApache-2.0"])
def test_instantiate_rejects_invalid_license_type(tmp_path: Path, license_type: str) -> None:
    with pytest.raises(ValueError, match="License"):
        instantiate("my_package", output_path=str(tmp_path), license_type=license_type)


@pytest.mark.parametrize("license_text", ["", "   "])
def test_instantiate_rejects_invalid_license_text(tmp_path: Path, license_text: str) -> None:
    with pytest.raises(ValueError, match="License text"):
        instantiate(
            "my_package",
            output_path=str(tmp_path),
            license_type="Custom-License",
            license_text=license_text,
        )


@pytest.mark.parametrize("license_text", ["Example\x00License", "Example\x1bLicense"])
def test_instantiate_rejects_license_text_control_characters(
    tmp_path: Path,
    license_text: str,
) -> None:
    with pytest.raises(ValueError, match="License text"):
        instantiate(
            "my_package",
            output_path=str(tmp_path),
            license_type="Custom-License",
            license_text=license_text,
        )


def test_instantiate_rejects_license_text_without_license(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="License text"):
        instantiate(
            "my_package",
            output_path=str(tmp_path),
            license_type="NONE",
            license_text="No license text",
        )


@pytest.mark.parametrize("artifact_kind", ["", "wheel", "SOURCE-TREE"])
def test_instantiate_rejects_invalid_artifact_kind(
    tmp_path: Path,
    artifact_kind: str,
) -> None:
    with pytest.raises(ValueError, match="Artifact kind"):
        instantiate("my_package", output_path=str(tmp_path), artifact_kind=artifact_kind)


def test_instantiate_rejects_overwrite_of_unmarked_directory(tmp_path: Path) -> None:
    unmarked_path = tmp_path / "my_package"
    unmarked_path.mkdir()
    (unmarked_path / "important.txt").write_text("do not delete", encoding="utf-8")

    with pytest.raises(FileExistsError, match="unmarked directory"):
        instantiate("my_package", output_path=str(tmp_path), overwrite=True)

    assert (unmarked_path / "important.txt").is_file()


def test_instantiate_rejects_overwrite_with_mismatched_marker(tmp_path: Path) -> None:
    created_path = instantiate("my_package", output_path=str(tmp_path))
    (created_path / MARKER_FILE_NAME).write_text(
        '{"distribution_name":"other-package","format_version":1,"module_name":"other_package"}\n',
        encoding="utf-8",
    )

    with pytest.raises(FileExistsError, match="does not match"):
        instantiate("my_package", output_path=str(tmp_path), overwrite=True)


def test_instantiate_rejects_overwrite_with_invalid_marker(tmp_path: Path) -> None:
    created_path = instantiate("my_package", output_path=str(tmp_path))
    (created_path / MARKER_FILE_NAME).write_text("not json", encoding="utf-8")

    with pytest.raises(FileExistsError, match="invalid marker"):
        instantiate("my_package", output_path=str(tmp_path), overwrite=True)


def test_instantiate_rejects_overwrite_target_containing_symlink(tmp_path: Path) -> None:
    created_path = instantiate("my_package", output_path=str(tmp_path))
    target_path = tmp_path / "target.txt"
    link_path = created_path / "linked.txt"
    target_path.write_text("target", encoding="utf-8")
    try:
        link_path.symlink_to(target_path)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"Symlink creation is not available in this environment: {error}")

    with pytest.raises(FileExistsError, match="symlink or junction"):
        instantiate("my_package", output_path=str(tmp_path), overwrite=True)

    assert link_path.is_symlink()


def test_instantiate_rejects_overwrite_of_non_directory_output(tmp_path: Path) -> None:
    output_file = tmp_path / "my_package"
    output_file.write_text("not a directory", encoding="utf-8")

    with pytest.raises(FileExistsError, match="not a regular directory"):
        instantiate("my_package", output_path=str(tmp_path), overwrite=True)


def test_reject_filesystem_links_rejects_source_symlink(tmp_path: Path) -> None:
    target_path = tmp_path / "target.txt"
    link_path = tmp_path / "link.txt"
    target_path.write_text("target", encoding="utf-8")
    try:
        link_path.symlink_to(target_path)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"Symlink creation is not available in this environment: {error}")

    with pytest.raises(ValueError, match="symlink"):
        _reject_filesystem_links(tmp_path)


def test_reject_filesystem_links_rejects_windows_junction(tmp_path: Path) -> None:
    target_path = tmp_path / "target"
    junction_path = tmp_path / "junction"
    target_path.mkdir()
    _create_windows_junction_or_skip(junction_path, target_path)

    with pytest.raises(ValueError, match="junction"):
        _reject_filesystem_links(tmp_path)


def test_filesystem_link_detection_rejects_windows_reparse_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reparse_point_attribute = 0x400

    class FakeStat:
        st_file_attributes = reparse_point_attribute

    class FakePath:
        def is_symlink(self) -> bool:
            return False

        def lstat(self) -> FakeStat:
            return FakeStat()

    monkeypatch.setattr(engine_module.os, "name", "nt")
    monkeypatch.setattr(
        engine_module.stat,
        "FILE_ATTRIBUTE_REPARSE_POINT",
        reparse_point_attribute,
        raising=False,
    )

    assert _is_filesystem_link(cast(Path, FakePath())) is True


def test_instantiate_rejects_overwrite_of_windows_junction(tmp_path: Path) -> None:
    target_path = tmp_path / "target"
    project_path = tmp_path / "my_package"
    target_path.mkdir()
    _create_windows_junction_or_skip(project_path, target_path)

    with pytest.raises(FileExistsError, match="not a regular directory"):
        instantiate("my_package", output_path=str(tmp_path), overwrite=True)


def _create_windows_junction_or_skip(junction_path: Path, target_path: Path) -> None:
    if sys.platform != "win32":
        pytest.skip("Windows junctions are only available on Windows.")

    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction_path), str(target_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"Junction creation is not available in this environment: {result.stderr}")


@pytest.mark.parametrize("invalid_name", ["", "123_package", "my.package", "class"])
def test_instantiate_rejects_invalid_package_names(tmp_path: Path, invalid_name: str) -> None:
    with pytest.raises(ValueError):
        instantiate(invalid_name, output_path=str(tmp_path))


def test_instantiate_normalizes_hyphenated_package_name(tmp_path: Path) -> None:
    created_path = instantiate("my-package", output_path=str(tmp_path))

    assert created_path == tmp_path / "my_package"
    assert (created_path / "src" / "my_package").is_dir()
    assert 'name = "my-package"' in (created_path / "pyproject.toml").read_text(
        encoding="utf-8"
    )
