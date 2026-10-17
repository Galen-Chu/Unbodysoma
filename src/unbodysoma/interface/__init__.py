"""Interface: the boundary between world, body and mind (senses and effectors)."""

from .exteroception import Exteroception
from .interoception import Interoception

__all__ = ["Exteroception", "Interoception"]
