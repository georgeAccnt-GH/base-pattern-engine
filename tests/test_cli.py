from __future__ import annotations

from pathlib import Path

import pytest
import tomlkit

from base_pattern_engine import cli


def test_cli_instantiates_package(tmp_path: Path, capsys) -> None:
    exit_code = cli.main(
        [
            "instantiate",
            "--name",
            "my_package",
            "--output-path",
            str(tmp_path),
            "--license",
            "MIT",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Created" in captured.out
    assert (tmp_path / "my_package" / "src" / "my_package").is_dir()
    assert not (tmp_path / "my_package" / "src" / "my_package" / "cli.py").exists()


def test_cli_uses_current_directory_by_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = cli.main(["instantiate", "--name", "default_location"])

    assert exit_code == 0
    assert (tmp_path / "default_location" / "pyproject.toml").is_file()


def test_cli_all_options_overwrite_replaces_existing_package(tmp_path: Path) -> None:
    cli.main(["instantiate", "--name", "all_arguments", "--output-path", str(tmp_path)])
    stale_file = tmp_path / "all_arguments" / "stale.txt"
    license_file = tmp_path / "LICENSE.template"
    stale_file.write_text("old content", encoding="utf-8")
    license_file.write_text("Example CLI license", encoding="utf-8")

    exit_code = cli.main(
        [
            "instantiate",
            "--name",
            "all_arguments",
            "--output-path",
            str(tmp_path),
            "--license",
            "Apache-2.0",
            "--license-file",
            str(license_file),
            "--owner-name",
            "Example Package Team",
            "--overwrite",
        ]
    )

    assert exit_code == 0
    assert not stale_file.exists()
    pyproject = tomlkit.parse(
        (tmp_path / "all_arguments" / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert (tmp_path / "all_arguments" / "LICENSE").read_text(encoding="utf-8") == (
        "Example CLI license\n"
    )
    assert pyproject["project"]["authors"] == [{"name": "Example Package Team"}]
    assert pyproject["project"]["license"] == {"file": "LICENSE"}
    assert "License :: OSI Approved :: MIT License" not in pyproject["project"]["classifiers"]
    assert "Apache-2.0" in (tmp_path / "all_arguments" / "README.md").read_text(
        encoding="utf-8"
    )


def test_cli_can_omit_generated_license(tmp_path: Path) -> None:
    exit_code = cli.main(
        [
            "instantiate",
            "--name",
            "unlicensed_package",
            "--output-path",
            str(tmp_path),
            "--license",
            "NONE",
        ]
    )

    assert exit_code == 0
    assert not (tmp_path / "unlicensed_package" / "LICENSE").exists()


def test_cli_overwrite_rejects_unmarked_directory(tmp_path: Path) -> None:
    unmarked_path = tmp_path / "my_package"
    unmarked_path.mkdir()
    (unmarked_path / "important.txt").write_text("do not delete", encoding="utf-8")

    _assert_cli_parser_error(
        [
            "instantiate",
            "--name",
            "my_package",
            "--output-path",
            str(tmp_path),
            "--overwrite",
        ]
    )

    assert (unmarked_path / "important.txt").is_file()


def test_cli_existing_output_without_overwrite_errors(tmp_path: Path) -> None:
    cli.main(["instantiate", "--name", "my_package", "--output-path", str(tmp_path)])

    _assert_cli_parser_error(["instantiate", "--name", "my_package", "--output-path", str(tmp_path)])


def test_cli_rejects_unknown_option(tmp_path: Path) -> None:
    _assert_cli_parser_error(
        [
            "instantiate",
            "--name",
            "my_package",
            "--output-path",
            str(tmp_path),
            "--unknown-option",
        ]
    )


def test_cli_rejects_invalid_license_type(tmp_path: Path) -> None:
    _assert_cli_parser_error(
        [
            "instantiate",
            "--name",
            "my_package",
            "--output-path",
            str(tmp_path),
            "--license",
            " ",
        ]
    )


def test_cli_rejects_missing_license_file(tmp_path: Path) -> None:
    _assert_cli_parser_error(
        [
            "instantiate",
            "--name",
            "my_package",
            "--output-path",
            str(tmp_path),
            "--license-file",
            str(tmp_path / "missing-license.txt"),
        ]
    )


def test_cli_rejects_symlinked_license_file(tmp_path: Path) -> None:
    target_path = tmp_path / "LICENSE.target"
    link_path = tmp_path / "LICENSE.link"
    target_path.write_text("Example license", encoding="utf-8")
    try:
        link_path.symlink_to(target_path)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"Symlink creation is not available in this environment: {error}")

    _assert_cli_parser_error(
        [
            "instantiate",
            "--name",
            "my_package",
            "--output-path",
            str(tmp_path),
            "--license-file",
            str(link_path),
        ]
    )

    assert not (tmp_path / "my_package").exists()


def test_cli_rejects_invalid_owner_name(tmp_path: Path) -> None:
    _assert_cli_parser_error(
        [
            "instantiate",
            "--name",
            "my_package",
            "--output-path",
            str(tmp_path),
            "--owner-name",
            " ",
        ]
    )


def _assert_cli_parser_error(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as error:
        cli.main(argv)

    assert error.value.code == 2
