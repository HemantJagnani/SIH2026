"""
AI Fallback package for normalization exceptions.

Usage:
    from normalization.ai_fallback import GeminiAiFallbackResolver, AiResolutionResponse
    from normalization.ai_fallback import handle_normalization_exception, ResolutionStatus

Spec §17: AI is exception-only — do not call for every observation.
"""

from .approval import (
    ResolutionStatus,
    approve_exception,
    handle_normalization_exception,
    list_quarantined,
    reject_exception,
)
from .models import AiResolutionResponse
from .resolver import GeminiAiFallbackResolver

__all__ = [
    "GeminiAiFallbackResolver",
    "AiResolutionResponse",
    "ResolutionStatus",
    "handle_normalization_exception",
    "approve_exception",
    "reject_exception",
    "list_quarantined",
]
