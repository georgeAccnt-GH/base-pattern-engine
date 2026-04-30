"""Package instantiation engine."""

from .core import PACKAGE_NAME, print_package_name
from .engine import instantiate


__all__ = ["PACKAGE_NAME", "instantiate", "print_package_name"]

__version__ = "0.1.0"
