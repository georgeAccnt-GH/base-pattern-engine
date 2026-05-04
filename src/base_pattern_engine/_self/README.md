# <package_title>

A standalone Python package generated from a package instantiation pattern.

This package contains its own source code and metadata. It does not depend on the package that generated it, and it does not include the generator's instantiation interface.

## Use

<generated_usage_section>

## Python Interface

```python
from <package_import_name> import DISTRIBUTION_NAME, MODULE_NAME, print_package_identity
```

Exposed package interface:

- `MODULE_NAME` contains the Python import package name.
- `DISTRIBUTION_NAME` contains the package distribution name.
- `print_package_identity()` prints both values.

Example:

```python
from <package_import_name> import print_package_identity

print_package_identity()
```

## Package Structure

```text
<package_distribution_name>/
<generated_package_structure_lines>
```

## License

<generated_license_label>
