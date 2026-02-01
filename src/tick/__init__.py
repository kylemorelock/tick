"""tick package."""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("tick")
except PackageNotFoundError:
    __version__ = "0.1.0"  # editable install or not installed
