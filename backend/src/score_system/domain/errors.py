class DomainError(ValueError):
    """A rule of the domain rejects the request; the API answers it with 422.

    Plain ValueErrors are not DomainErrors: they mean a bug and give a server error.
    """
