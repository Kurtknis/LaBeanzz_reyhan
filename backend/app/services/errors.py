class ServiceError(Exception):
    """A business-rule failure that maps directly onto an HTTP response."""

    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.message = message
        self.status = status
