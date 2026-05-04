"""Package instantiation engine."""

from .core import DISTRIBUTION_NAME, MODULE_NAME, print_package_identity
from .engine import instantiate


__all__ = [
    "DISTRIBUTION_NAME",
    "MODULE_NAME",
    "instantiate",
    "print_package_identity",
]

__version__ = "0.1.0"
