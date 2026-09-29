class InvalidIdentifierError(ValueError):
    """Raised when a speaker or recording ID has an invalid format."""


class InvalidRecordError(ValueError):
    """Raised when a CSV row contains invalid data."""