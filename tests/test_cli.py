from __future__ import annotations

from pathlib import Path

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


def test_cli_overwrite_replaces_existing_package(tmp_path: Path) -> None:
    cli.main(["instantiate", "--name", "my_package", "--output-path", str(tmp_path)])
    stale_file = tmp_path / "my_package" / "stale.txt"
    stale_file.write_text("old content", encoding="utf-8")

    exit_code = cli.main(
        [
            "instantiate",
            "--name",
            "my_package",
            "--output-path",
            str(tmp_path),
            "--overwrite",
        ]
    )

    assert exit_code == 0
    assert not stale_file.exists()


def test_cli_existing_output_without_overwrite_errors(tmp_path: Path) -> None:
    cli.main(["instantiate", "--name", "my_package", "--output-path", str(tmp_path)])

    try:
        cli.main(["instantiate", "--name", "my_package", "--output-path", str(tmp_path)])
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("Expected parser error for existing output without --overwrite.")


def test_cli_rejects_force_flag(tmp_path: Path) -> None:
    try:
        cli.main(
            [
                "instantiate",
                "--name",
                "my_package",
                "--output-path",
                str(tmp_path),
                "--force",
            ]
        )
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("Expected parser error for unsupported --force flag.")
