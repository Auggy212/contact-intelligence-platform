from fastapi import HTTPException, status


class AppError(Exception):
    """Base for all application-level errors."""


class AuthenticationError(AppError):
    pass


class AuthorizationError(AppError):
    pass


class NotFoundError(AppError):
    pass


class ConflictError(AppError):
    pass


class QuotaExceededError(AppError):
    pass


class ValidationError(AppError):
    pass


class ParseError(AppError):
    pass


class StorageError(AppError):
    pass


class AIError(AppError):
    pass


# ── FastAPI HTTP exception converters ─────────────────────────────────────────

def not_found(resource: str = "Resource") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} not found")


def forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


def unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


def conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def quota_exceeded(detail: str = "Quota exceeded for your subscription plan") -> HTTPException:
    return HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=detail)
