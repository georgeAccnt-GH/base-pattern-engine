"""Command line interface for package instantiation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from .engine import DEFAULT_LICENSE_TYPE, DEFAULT_OWNER_NAME, _is_filesystem_link, instantiate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="base-pattern-engine",
        description="Instantiate a standalone Python package from this installed package.",
    )
    subparsers = parser.add_subparsers(dest="command")

    instantiate_parser = subparsers.add_parser(
        "instantiate",
        help="Create a new independent package.",
    )
    instantiate_parser.add_argument(
        "--name",
        dest="package_name",
        required=True,
        help="New Python package name, for example my_package.",
    )
    instantiate_parser.add_argument(
        "--output-path",
        default=".",
        help="Directory where the new project folder will be created.",
    )
    instantiate_parser.add_argument(
        "--license",
        dest="license_type",
        default=DEFAULT_LICENSE_TYPE,
        help="Generated package license expression. Use NONE to omit license metadata and the LICENSE file.",
    )
    instantiate_parser.add_argument(
        "--license-file",
        help="Path to custom license text to write as the generated package LICENSE file.",
    )
    instantiate_parser.add_argument(
        "--owner-name",
        default=DEFAULT_OWNER_NAME,
        help="Generated package author and license copyright holder.",
    )
    instantiate_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the generated package directory if it already exists.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "instantiate":
        try:
            license_text = _read_license_file(args.license_file)
            created_path = instantiate(
                package_name=args.package_name,
                output_path=args.output_path,
                license_type=args.license_type,
                overwrite=args.overwrite,
                owner_name=args.owner_name,
                license_text=license_text,
            )
        except (FileExistsError, OSError, ValueError) as error:
            parser.error(str(error))

        print(f"Created {created_path}")
        return 0

    parser.print_help()
    return 0


def _read_license_file(license_file: Optional[str]) -> Optional[str]:
    if license_file is None:
        return None

    license_path = Path(license_file).expanduser()
    if _is_filesystem_link(license_path):
        raise ValueError(f"Refusing to read symlinked or junctioned license file: {license_path}")
    if not license_path.is_file():
        raise FileNotFoundError(f"License file does not exist or is not a regular file: {license_path}")

    return license_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
