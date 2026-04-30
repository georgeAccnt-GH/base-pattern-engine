# <package_title>

A standalone Python package generated from a package instantiation pattern.

This package contains its own source code and metadata. It does not depend on the package that generated it, and it does not include the generator's instantiation interface.

## Install

From this package directory:

```shell
python -m pip install .
```

## Python Interface

```python
from <package_import_name> import PACKAGE_NAME, print_package_name
```

Exposed package interface:

- `PACKAGE_NAME` contains the package distribution name.
- `print_package_name()` prints `PACKAGE_NAME`.

Example:

```python
from <package_import_name> import print_package_name

print_package_name()
```

## Package Structure

```text
<package_distribution_name>/
  pyproject.toml
<generated_license_and_readme_file_lines>
  <generated_marker_file_name>
  src/<package_import_name>/
```

## License

<generated_license_label>
