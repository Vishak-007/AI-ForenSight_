"""
AI-ForenSight - Module: Translation Errors

Exception hierarchy for the translation pipeline. A dependency/model
failure must always surface loudly with an actionable message - never be
caught and silently downgraded into a bad or partial translation.
"""


class TranslationDependencyError(RuntimeError):
    """Base class for any failure loading a required library or model."""


class MissingDependencyError(TranslationDependencyError):
    """A required Python package is not installed."""

    def __init__(self, package_name, pip_name=None, extra=""):
        pip_name = pip_name or package_name
        message = (
            f"ERROR: required package '{package_name}' is not installed.\n"
            f"  Run: pip install {pip_name}"
        )
        if extra:
            message += f"\n  {extra}"
        super().__init__(message)


class ModelLoadError(TranslationDependencyError):
    """A required model could not be loaded (missing, corrupt, or no
    network access on first download)."""

    def __init__(self, model_name, remedy):
        message = (
            f"ERROR: could not load model '{model_name}'.\n"
            f"  {remedy}"
        )
        super().__init__(message)
