"""
Core structures for the Deterministic Normalization pipeline.

Spec §14, §15:
- Deterministic exact matches only.
- Ambiguous values result in NormalizationException.
- Output preserves raw and normalized pairs.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

PIPELINE_VERSION = "2.0.0"


class NormalizationResult(BaseModel, Generic[T]):
    """
    Standard output from any normalization function.
    Preserves the raw value alongside the parsed value per Spec §15.
    """
    model_config = ConfigDict(frozen=True)

    raw_value: str
    normalized_value: T | None = None
    is_success: bool = False
    confidence: float = 0.0


class NormalizationException(Exception):
    """
    Raised when deterministic normalization fails.
    This explicitly flags the value for later AI resolution or manual review (§41).
    """

    def __init__(self, field_name: str, raw_value: str, message: str):
        super().__init__(f"Failed to normalize {field_name} '{raw_value}': {message}")
        self.field_name = field_name
        self.raw_value = raw_value
        self.message = message
