class SufeCliError(RuntimeError):
    exit_code = 1

    def __init__(self, message: str, *, exit_code: int | None = None) -> None:
        super().__init__(message)
        if exit_code is not None:
            self.exit_code = exit_code


class AuthConfigMissingError(SufeCliError):
    pass


class AuthExpiredError(SufeCliError):
    pass


class RequestFailedError(SufeCliError):
    pass


class InvalidResponseError(SufeCliError):
    pass


class UploadFailedError(SufeCliError):
    pass
