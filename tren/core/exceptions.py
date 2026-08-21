"""
Exception hierarchy for TrenTorch CLI.
"""

class TrenTorchCLIError(Exception):
    """Base exception for all CLI errors."""
    pass

class ValidationError(TrenTorchCLIError):
    """Raised when validation fails."""
    pass

class ExecutionError(TrenTorchCLIError):
    """Raised when command execution fails."""
    pass

class EnvironmentError(TrenTorchCLIError):
    """Raised when environment setup is invalid."""
    pass

class ModuleNotFoundError(TrenTorchCLIError):
    """Raised when a requested module is not found."""
    pass
