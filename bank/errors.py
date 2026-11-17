class BankError(Exception):
    """Base domain error. `status` maps to an HTTP status in the API."""
    status = 400


class ValidationError(BankError):
    status = 422


class NotFoundError(BankError):
    status = 404


class ConflictError(BankError):
    status = 409
