# Base Pattern Engine

A minimal Python package instantiation tool that creates independent generated artifacts: a pip-installable `package` artifact or a `source-tree` artifact.

This repository is a personal project and does not contain any proprietary Microsoft or client code or information.

## What it does

- Generates a new `package` artifact or `source-tree` artifact from itself.
- Produces code with no runtime dependency on the source package.
- Creates independent generated artifacts that can be extended and licensed separately.

## Terminology

These docs use a few terms consistently:

- **Base Pattern Engine** is the human-readable project name.
- `base-pattern-engine` is the installed distribution name and CLI command.
- `base_pattern_engine` is the Python import package name for the engine API.
- A **generated artifact** is any output created by `base-pattern-engine instantiate`.
- A **`package` artifact** is a generated, pip-installable package with `pyproject.toml`.
- A **`source-tree` artifact** is generated source-only output without packaging metadata.

After those terms are introduced, "the engine" only refers to the installed generator.

## Workflow

For a guided canonical walkthrough, see [docs/happy_path_tutorial.md](docs/happy_path_tutorial.md).

Use a pinned tag or commit SHA for reproducible installs:

```shell
python -m pip install git+https://github.com/georgeAccnt-GH/base-pattern-engine.git@<tag-or-commit-sha>
base-pattern-engine instantiate --name my_package --license MIT
```

Create a `source-tree` artifact when you want generated code to copy into another project or import with `PYTHONPATH`:

```shell
base-pattern-engine instantiate --name my_code --artifact-kind source-tree --output-path ./generated
```

When `base-pattern-engine` changes, upgrade to another pinned ref and re-instantiate the generated package:

```shell
python -m pip install --upgrade git+https://github.com/georgeAccnt-GH/base-pattern-engine.git@<new-tag-or-commit-sha>
base-pattern-engine instantiate --name my_package --license MIT --overwrite
```

When you no longer need `base-pattern-engine`, uninstall it:

```shell
python -m pip uninstall base-pattern-engine
```

For active development, you can install directly from the moving `main` branch:

```shell
python -m pip install git+https://github.com/georgeAccnt-GH/base-pattern-engine.git@main
```

## CLI

Instantiate a `package` artifact:

```shell
base-pattern-engine instantiate --name my_package --license MIT
```

Instantiate a `source-tree` artifact:

```shell
base-pattern-engine instantiate --name my_code --artifact-kind source-tree --output-path ./generated
```

Use all options when you need a custom output location, generated artifact license, owner, and overwrite behavior:

```shell
base-pattern-engine instantiate --name my_package --artifact-kind package --output-path . --license Apache-2.0 --license-file ./LICENSE-APACHE-2.0 --owner-name "Package contributors" --overwrite
```

CLI options:

- `--name` sets the generated Python package name.
- `--output-path` sets the directory where the generated project folder is created.
- `--artifact-kind` selects the generated artifact kind: `package` for a pip-installable package, or `source-tree` for source-only code. The default is `package`.
- `--license` sets the generated artifact license expression. Use `NONE` to omit generated license metadata and the `LICENSE` file.
- `--license-file` reads custom license text from a regular, non-linked file and writes it into the generated artifact `LICENSE` file; the file should match the selected generated artifact license.
- `--owner-name` sets the generated package author and, for generated MIT licenses, the copyright holder.
- `--overwrite` replaces an existing generated artifact directory only when it has a matching generated-package marker.

A generated `package` artifact has this structure:

```text
my_package/
  pyproject.toml
  LICENSE
  README.md
  .package-instantiation.json
  src/my_package/
```

A generated `source-tree` artifact has this structure:

```text
my_code/
  LICENSE
  README.md
  .package-instantiation.json
  src/my_code/
```

The generated `LICENSE` file is omitted in either artifact kind when the selected license is `NONE`, and can also be omitted for custom single-line license expressions that do not provide custom license text.

## Artifact Kinds

`artifact_kind="package"` is the default. It emits a regular pip-installable package with `pyproject.toml`, generated license metadata, generated README, marker file, and `src/<package_name>/`.

`artifact_kind="source-tree"` emits a `source-tree` artifact with generated README, optional generated `LICENSE`, marker file, and `src/<package_name>/`. It omits `pyproject.toml`, build configuration, package metadata, script entry points, package-data settings, and dependency metadata.

Both artifact kinds rewrite package identity, remove the generator surface, preserve overwrite safety, and are independent from `base-pattern-engine` at runtime.

## Generated Packages

A generated package is a `package` artifact. It is standalone, does not retain a runtime dependency on the source package, and does not include the `base-pattern-engine` generation CLI or `instantiate()` API.

Generated packages expose copied package functionality, such as `MODULE_NAME`, `DISTRIBUTION_NAME`, and `print_package_identity()`, but not the instantiation interface. `MODULE_NAME` is the Python import package name, and `DISTRIBUTION_NAME` is the package distribution name. In `base-pattern-engine`, `print_package_identity()` prints both `base_pattern_engine` and `base-pattern-engine`; in a generated package, it prints both generated values, such as `my_package` and `my-package`.

For pip-installable `package` artifacts, packaging metadata and pip use the distribution name, while Python import statements use the module name. `base-pattern-engine` normalizes `--name` into a module name by lowercasing it and replacing hyphens with underscores, then derives the distribution name by replacing underscores with hyphens. For example, `--name my_package` and `--name my-package` both produce module name `my_package` and distribution name `my-package`.

The `base-pattern-engine` project itself is MIT licensed. Generated artifacts are intended to be independent generated outputs: the artifact owner may license, modify, distribute, and use a generated artifact under the terms they choose, including MIT, Apache-2.0, proprietary terms, or no published license. This generated-output permission applies to material produced from this project; third-party code, data, or assets added later remain subject to their own terms.

Generated artifact licensing is selected independently from the `base-pattern-engine` license:

- `package` artifacts default to MIT with `Package contributors` as the author and license copyright holder.
- Pass `--owner-name` or `owner_name` to use a project-specific owner.
- Use `--license NONE` or `license_type="NONE"` to omit generated license metadata and the `LICENSE` file.
- Use a custom single-line license expression, such as `Apache-2.0`, to write license metadata.
- Add `--license-file path/to/LICENSE` or `license_text` to include custom license text for the selected generated package license.

`source-tree` artifacts have no `pyproject.toml`, so source-tree license options only control the generated `LICENSE` file and README license label.

Overwrite is intentionally conservative: `base-pattern-engine` only overwrites directories that contain its generated-package marker file, and it refuses to copy symlinked, junctioned, or Windows reparse-point source or metadata paths.

Before returning, `base-pattern-engine` validates that generated text files do not contain unresolved package-template placeholders.

## Python API

```python
from base_pattern_engine import instantiate

instantiate("my_package")

instantiate(
    package_name="my_code",
    output_path="./generated",
    artifact_kind="source-tree",
)
```

The Python API with all arguments is:

```python
from base_pattern_engine import instantiate

instantiate(
    package_name="my_package",
    output_path=".",
    artifact_kind="package",
    license_type="MIT",
    overwrite=True,
    owner_name="Package contributors",
    license_text=None,
)
```

Use `overwrite=True` only when replacing an existing generated artifact directory.

## How it works

`base-pattern-engine` locates its installed source with Python introspection, copies that source with `shutil.copytree`, rewrites package names and imports with direct string replacement, removes the generator-only CLI and instantiation API from the generated artifact, validates the generated output, and edits generated package metadata with TOML-aware transforms when creating `package` artifacts.

## Scope

- Generates a new `package` artifact or `source-tree` artifact from its installed package source
- Ensures the generated artifact has no dependency on the source
- Demonstrates one-way code propagation
- Does not implement function-level extraction
- Does not include production features or domain-specific logic

## Security Model

`base-pattern-engine` is intended for trusted local development workflows. Run it against source trees and output directories that you control, and avoid concurrently modifying the source package tree or output parent directory while instantiation is running.

`base-pattern-engine` refuses to copy symlinked, junctioned, or Windows reparse-point source and metadata paths, validates generated text for unresolved placeholders, and only overwrites directories that contain a matching generated-package marker. These checks reduce accidental or unsafe writes, but they are not a sandbox for processing untrusted or concurrently mutated filesystem trees.

The `.package-instantiation.json` marker is an internal overwrite guard. Do not create or edit it manually; a matching marker identifies a prior generated artifact, but it is not a trust boundary for untrusted directories.

## License

`base-pattern-engine` is licensed under the MIT License.

The MIT License applies to this generator project. Artifacts generated by `base-pattern-engine` are independent generated outputs and may be licensed under the terms selected by the generated artifact owner. The CLI and Python API write generated artifact license information according to `--license`, `--license-file`, `license_type`, and `license_text`.
