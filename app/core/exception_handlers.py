"""Custom exception handlers for the AI Analysis Service."""

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class AnalysisException(Exception):
    """Base exception for analysis-related errors."""
    
    def __init__(self, message: str, status_code: int = HTTPStatus.BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class DatabaseException(AnalysisException):
    """Database-related exceptions."""
    
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, HTTPStatus.INTERNAL_SERVER_ERROR)


class ExternalServiceException(AnalysisException):
    """External service-related exceptions."""
    
    def __init__(self, message: str = "External service unavailable"):
        super().__init__(message, HTTPStatus.SERVICE_UNAVAILABLE)


class ValidationException(AnalysisException):
    """Validation-related exceptions."""
    
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, HTTPStatus.UNPROCESSABLE_ENTITY)


class WhatsAppException(AnalysisException):
    """Base exception for WhatsApp automation errors."""
    
    def __init__(self, message: str, error_code: str, status_code: int = HTTPStatus.BAD_REQUEST):
        self.error_code = error_code
        super().__init__(message, status_code)


class DisplayUnavailableError(WhatsAppException):
    """Raised when PyAutoGUI display is unavailable."""
    
    def __init__(self, message: str = "Cannot connect to Linux display. PyAutoGUI requires DISPLAY to be set."):
        super().__init__(message, "DISPLAY_NOT_AVAILABLE", HTTPStatus.BAD_REQUEST)


class BrowserInitializationError(WhatsAppException):
    """Raised when browser initialization fails."""
    
    def __init__(self, message: str = "Failed to initialize browser for WhatsApp automation."):
        super().__init__(message, "BROWSER_INIT_FAILED", HTTPStatus.INTERNAL_SERVER_ERROR)


class SenderInitializationError(WhatsAppException):
    """Raised when WhatsApp sender fails to initialize."""
    
    def __init__(self, message: str = "WhatsApp sender initialization failed."):
        super().__init__(message, "SENDER_INIT_FAILED", HTTPStatus.BAD_REQUEST)


class InvalidPhoneError(WhatsAppException):
    """Raised when phone number validation fails."""
    
    def __init__(self, phone: str):
        super().__init__(f"Invalid phone number: {phone}", "INVALID_PHONE", HTTPStatus.BAD_REQUEST)


class LeadNotFoundError(WhatsAppException):
    """Raised when a lead cannot be found in database."""
    
    def __init__(self, lead_id: str):
        super().__init__(f"Lead not found: {lead_id}", "LEAD_NOT_FOUND", HTTPStatus.NOT_FOUND)


class MessageGenerationError(WhatsAppException):
    """Raised when message generation fails."""
    
    def __init__(self, message: str = "Failed to generate WhatsApp message."):
        super().__init__(message, "MESSAGE_GENERATION_FAILED", HTTPStatus.BAD_REQUEST)


async def analysis_exception_handler(
    request: Request, exc: AnalysisException
) -> JSONResponse:
    """Handle analysis exceptions."""
    response_content = {
        "success": False,
        "message": exc.message,
        "error": exc.__class__.__name__,
    }
    if hasattr(exc, 'error_code'):
        response_content["code"] = exc.error_code
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_content,
    )


async def validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle validation exceptions."""
    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation failed",
            "errors": exc.errors(),
        },
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle generic exceptions."""
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected error occurred",
            "error": str(exc),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(AnalysisException, analysis_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
