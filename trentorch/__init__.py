"""
TrenTorch - Pure NumPy Deep Learning Framework for Systems Engineering.
"""

from pathlib import Path as _Path
from .core.platform import setup_platform_runtime, PlatformDetector

# Initialize platform hooks automatically on import
ACTIVE_PLATFORM = setup_platform_runtime()

def _get_version() -> str:
    try:
        pyproject_path = _Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            for line in content.splitlines():
                if line.strip().startswith("version"):
                    return line.split("=")[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "0.1.0"

__version__ = _get_version()

# Forward exports from core
try:
    from tinytorch.core.tensor import Tensor
except ImportError:
    try:
        from .core.tensor import Tensor
    except ImportError:
        Tensor = None
