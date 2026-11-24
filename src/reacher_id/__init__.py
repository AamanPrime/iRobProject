"""Physics and dataset foundation for reacher inverse-dynamics learning."""

from .config import Phase1Config, load_config
from .dynamics import MujocoDynamics
from .environment import inspect_runtime, load_reacher

__all__ = [
    "MujocoDynamics",
    "Phase1Config",
    "inspect_runtime",
    "load_config",
    "load_reacher",
]

__version__ = "0.1.0"
