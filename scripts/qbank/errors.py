"""Errors raised by qbank infrastructure."""


class QbankError(Exception):
    """Base class for expected qbank errors."""


class ConfigError(QbankError):
    """Invalid or unavailable project configuration."""


class SchemaValidationError(QbankError):
    """Data does not satisfy a qbank schema."""


class SourceValidationError(QbankError):
    """A configured source is invalid."""


class TransitionError(QbankError):
    """A state transition is not allowed."""


class ExportError(QbankError):
    """An export operation failed."""
