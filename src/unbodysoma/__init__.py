"""Unbodysoma: an embodied human simulation engine with a mind grown from its body."""

from .core import Engine, Module
from .presets import build_minimal_human

__version__ = "0.0.1"

__all__ = ["Engine", "Module", "__version__", "build_minimal_human"]
