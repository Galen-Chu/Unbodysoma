"""Unbodysoma: an embodied human simulation engine with a mind grown from its body."""

from .core import Engine, Module
from .presets import build_grid_human, build_minimal_human

__version__ = "0.2.0"  # single source: pyproject reads it

__all__ = ["Engine", "Module", "__version__", "build_grid_human", "build_minimal_human"]
