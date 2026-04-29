
# Base Pattern Engine

A minimal Python package that can reproduce itself.

This repository is a personal project and does not contain any proprietary Microsoft or client code or information.

This repository demonstrates a simple pattern instantiation mechanism:
- copy installed package source
- rename and transform it
- generate a new, fully independent Python package

## Client-side Workflow

Install directly from a Git branch:

```shell
python -m pip install git+https://github.com/georgeAccnt-GH/base-pattern-engine.git@main
```

Instantiate a standalone package:

```shell
base-pattern-engine instantiate --name my_package --license MIT
```

The command creates:

```text
my_package/
  pyproject.toml
  LICENSE
  README.md
  src/my_package/
```

When this repository is updated, upgrade the installed engine and instantiate again:

```shell
python -m pip install --upgrade git+https://github.com/georgeAccnt-GH/base-pattern-engine.git@main
base-pattern-engine instantiate --name my_package --license MIT --overwrite
```

If the branch changed but the package version did not, use `--force-reinstall` with pip:

```shell
python -m pip install --upgrade --force-reinstall git+https://github.com/georgeAccnt-GH/base-pattern-engine.git@main
```

When you no longer need the engine, uninstall it:

```shell
python -m pip uninstall base-pattern-engine
```

The generated package is standalone and does not retain a dependency on the source package. It is a regular pip-installable package and does not include this engine's self-copying CLI or `instantiate()` API.

## Python API

```python
from base_pattern_engine import instantiate

instantiate("my_package")
```

To replace an existing generated package directory from Python, pass `overwrite=True`.

Generated packages expose copied package functionality, such as `PACKAGE_NAME` and `print_package_name()`, but not the instantiation interface. In `base-pattern-engine`, `print_package_name()` prints `base-pattern-engine`; in a generated package, it prints the generated distribution name, such as `my-package`.

## How it works

The package locates its installed source with Python introspection, copies that source with `shutil.copytree`, and rewrites package names, imports, metadata, and the CLI entry point with direct string replacement.

## What it does

- Generates a new pip-installable package from its installed package source
- Ensures the generated package has no dependency on the source
- Demonstrates one-way code propagation

## Scope

This is a minimal demonstration of the mechanism. It does not include production features or domain-specific logic.

## License

MIT


