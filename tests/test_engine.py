from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from base_pattern_engine import instantiate, print_package_name


def test_instantiate_creates_standalone_package(tmp_path: Path) -> None:
    created_path = instantiate("my_package", output_path=str(tmp_path), license_type="MIT")

    assert created_path == tmp_path / "my_package"
    assert (created_path / "pyproject.toml").is_file()
    assert (created_path / "LICENSE").is_file()
    assert (created_path / "README.md").is_file()
    assert (created_path / "src" / "my_package" / "__init__.py").is_file()
    assert (created_path / "src" / "my_package" / "core.py").is_file()


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
    assert "my_package" in all_text
    assert "my-package" in all_text


def test_package_name_method_prints_instantiated_package_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    created_path = instantiate("my_package", output_path=str(tmp_path))
    generated_src_path = str(created_path / "src")

    print_package_name()
    source_output = capsys.readouterr().out

    sys.path.insert(0, generated_src_path)
    try:
        generated_package = importlib.import_module("my_package")
        generated_package.print_package_name()
        generated_output = capsys.readouterr().out
        assert not hasattr(generated_package, "instantiate")
    finally:
        sys.path.remove(generated_src_path)
        sys.modules.pop("my_package", None)

    assert source_output == "base-pattern-engine\n"
    assert generated_output == "my-package\n"


def test_instantiated_package_has_no_instantiation_interface(tmp_path: Path) -> None:
    created_path = instantiate("my_package", output_path=str(tmp_path))
    package_path = created_path / "src" / "my_package"
    pyproject_text = (created_path / "pyproject.toml").read_text(encoding="utf-8")
    readme_text = (created_path / "README.md").read_text(encoding="utf-8")

    assert not (package_path / "engine.py").exists()
    assert not (package_path / "cli.py").exists()
    assert not (package_path / "_self").exists()
    assert "[project.scripts]" not in pyproject_text
    assert "[tool.setuptools.package-data]" not in pyproject_text
    assert "reproduce itself" not in pyproject_text
    assert "instantiate" not in (package_path / "__init__.py").read_text(encoding="utf-8")
    assert "<package_" not in readme_text
    assert "# My Package" in readme_text
    assert "from my_package import PACKAGE_NAME, print_package_name" in readme_text
    assert "my-package/" in readme_text


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


def test_instantiate_rejects_unsupported_license(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported license"):
        instantiate("my_package", output_path=str(tmp_path), license_type="Apache-2.0")
