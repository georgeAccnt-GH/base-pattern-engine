# Base Pattern Engine

A minimal Python package instantiation engine.

This repository is a personal project and does not contain any proprietary Microsoft or client code or information.

This repository demonstrates a simple pattern instantiation mechanism:

- copy installed package source
- rename and transform it
- generate a new, fully independent Python package

## Workflow

Use a pinned tag or commit SHA for reproducible installs:

```shell
python -m pip install git+https://github.com/georgeAccnt-GH/base-pattern-engine.git@<tag-or-commit-sha>
base-pattern-engine instantiate --name my_package --license MIT
```

When the engine changes, upgrade to another pinned ref and re-instantiate the generated package:

```shell
python -m pip install --upgrade git+https://github.com/georgeAccnt-GH/base-pattern-engine.git@<new-tag-or-commit-sha>
base-pattern-engine instantiate --name my_package --license MIT --overwrite
```

When you no longer need the engine, uninstall it:

```shell
python -m pip uninstall base-pattern-engine
```

For active development, you can install directly from the moving `main` branch:

```shell
python -m pip install git+https://github.com/georgeAccnt-GH/base-pattern-engine.git@main
```

## CLI

Instantiate a standalone package:

```shell
base-pattern-engine instantiate --name my_package --license MIT
```

Use all options when you need a custom output location, generated package license, owner, and overwrite behavior:

```shell
base-pattern-engine instantiate --name my_package --output-path . --license Apache-2.0 --license-file ./LICENSE --owner-name "Package contributors" --overwrite
```

CLI options:

- `--name` sets the generated Python package name.
- `--output-path` sets the directory where the generated project folder is created.
- `--license` sets the generated package license expression. Use `NONE` to omit generated license metadata and the `LICENSE` file.
- `--license-file` reads custom license text to write into the generated package `LICENSE` file.
- `--owner-name` sets the generated package author and MIT license copyright holder.
- `--overwrite` replaces an existing generated package directory only when it has a matching generated-package marker.

The command creates:

```text
my_package/
  pyproject.toml
  LICENSE
  README.md
  .package-instantiation.json
  src/my_package/
```

## Generated Packages

The generated package is standalone and does not retain a dependency on the source package. It is a regular pip-installable package and does not include this engine's generation CLI or `instantiate()` API.

Generated packages expose copied package functionality, such as `PACKAGE_NAME` and `print_package_name()`, but not the instantiation interface. In `base-pattern-engine`, `print_package_name()` prints `base-pattern-engine`; in a generated package, it prints the generated distribution name, such as `my-package`.

The `base-pattern-engine` project is MIT licensed, but each generated package chooses its own license independently:

- Generated packages default to MIT with `Package contributors` as the author and license copyright holder.
- Pass `--owner-name` or `owner_name` to use a project-specific owner.
- Use `--license NONE` or `license_type="NONE"` to omit generated license metadata and the `LICENSE` file.
- Use a custom single-line license expression, such as `Apache-2.0`, to write license metadata.
- Add `--license-file path/to/LICENSE` or `license_text` to include custom license text.

Overwrite is intentionally conservative: the engine only overwrites directories that contain its generated-package marker file, and it refuses to copy symlinked or junctioned source or metadata paths.

## Python API

```python
from base_pattern_engine import instantiate

instantiate("my_package")
```

The Python API with all arguments is:

```python
from base_pattern_engine import instantiate

instantiate(
    package_name="my_package",
    output_path=".",
    license_type="MIT",
    overwrite=True,
    owner_name="Package contributors",
    license_text=None,
)
```

Use `overwrite=True` only when replacing an existing generated package directory.

## How it works

The package locates its installed source with Python introspection, copies that source with `shutil.copytree`, rewrites package names and imports with direct string replacement, and edits generated metadata with TOML-aware transforms.

## Scope

- Generates a new pip-installable package from its installed package source
- Ensures the generated package has no dependency on the source
- Demonstrates one-way code propagation
- Does not include production features or domain-specific logic

## License

MIT. This is the license for `base-pattern-engine`; generated packages choose their own license independently.
