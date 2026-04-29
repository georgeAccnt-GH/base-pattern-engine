"""Command line interface for package instantiation."""

from __future__ import annotations

import argparse

from .engine import instantiate


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
        default="MIT",
        help="License to write into the new package. Currently supports MIT.",
    )
    instantiate_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the generated package directory if it already exists.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "instantiate":
        try:
            created_path = instantiate(
                package_name=args.package_name,
                output_path=args.output_path,
                license_type=args.license_type,
                overwrite=args.overwrite,
            )
        except (FileExistsError, ValueError) as error:
            parser.error(str(error))

        print(f"Created {created_path}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
