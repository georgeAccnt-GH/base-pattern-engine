# Base Pattern Engine

A minimal Python package that can reproduce itself into a new, independent, pip-installable package.

This repository is a personal project and does not contain any proprietary Microsoft or client code or information.

## What it does

- Generates a new standalone Python package from itself.
- Produces code with no runtime dependency on the source package.
- Creates independent packages that can be extended and licensed separately.

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
base-pattern-engine instantiate --name my_package --output-path . --license Apache-2.0 --license-file ./LICENSE-APACHE-2.0 --owner-name "Package contributors" --overwrite
```

CLI options:

- `--name` sets the generated Python package name.
- `--output-path` sets the directory where the generated project folder is created.
- `--license` sets the generated package license expression. Use `NONE` to omit generated license metadata and the `LICENSE` file.
- `--license-file` reads custom license text from a regular, non-symlinked file and writes it into the generated package `LICENSE` file; the file should match the selected generated package license.
- `--owner-name` sets the generated package author and, for generated MIT licenses, the copyright holder.
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

The generated package is standalone and does not retain a runtime dependency on the source package. It is a regular pip-installable package and does not include this engine's generation CLI or `instantiate()` API.

Generated packages expose copied package functionality, such as `PACKAGE_NAME` and `print_package_name()`, but not the instantiation interface. In `base-pattern-engine`, `print_package_name()` prints `base-pattern-engine`; in a generated package, it prints the generated distribution name, such as `my-package`.

The `base-pattern-engine` project itself is MIT licensed. Generated packages are intended to be independent generated outputs: the package owner may license, modify, distribute, and use a generated package under the terms they choose, including MIT, Apache-2.0, proprietary terms, or no published license. This generated-output permission applies to material produced from this project; third-party code, data, or assets added later remain subject to their own terms.

Generated package licensing is selected independently from the engine license:

- Generated packages default to MIT with `Package contributors` as the author and license copyright holder.
- Pass `--owner-name` or `owner_name` to use a project-specific owner.
- Use `--license NONE` or `license_type="NONE"` to omit generated license metadata and the `LICENSE` file.
- Use a custom single-line license expression, such as `Apache-2.0`, to write license metadata.
- Add `--license-file path/to/LICENSE` or `license_text` to include custom license text for the selected generated package license.

Overwrite is intentionally conservative: the engine only overwrites directories that contain its generated-package marker file, and it refuses to copy symlinked or junctioned source or metadata paths.

Before returning, the engine validates that generated text files do not contain unresolved package-template placeholders.

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

The package locates its installed source with Python introspection, copies that source with `shutil.copytree`, rewrites package names and imports with direct string replacement, removes the engine-only CLI and instantiation API from the generated package, validates the generated output, and edits generated metadata with TOML-aware transforms.

## Scope

- Generates a new pip-installable package from its installed package source
- Ensures the generated package has no dependency on the source
- Demonstrates one-way code propagation
- Does not include production features or domain-specific logic

## License

`base-pattern-engine` is licensed under the MIT License.

The MIT License applies to this generator project. Packages generated by `base-pattern-engine` are independent generated outputs and may be licensed under the terms selected by the generated package owner. The CLI and Python API write generated package license metadata according to `--license`, `--license-file`, `license_type`, and `license_text`.
