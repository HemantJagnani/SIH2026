"""
Pydantic model for the AI resolver's structured response.

Spec §18: The AI output must return a structured JSON response that itself
passes Pydantic validation before being used anywhere in the pipeline.

The AI must return exactly this shape. Any deviation is treated as a
resolution failure.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AiResolutionResponse(BaseModel):
    """
    Structured response from the Gemini AI fallback resolver.
    
    Spec §18 required fields:
    - candidate_value: The proposed normalized value
    - confidence: Float 0.0–1.0
    - needs_review: Whether human review is required
    - reason: Short explanation of why this candidate was chosen
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str = Field(
        ...,
        description="The field being resolved (e.g., 'airline', 'airport').",
    )
    raw_value: str = Field(
        ...,
        description="The exact raw string that could not be deterministically normalized.",
    )
    candidate_value: str = Field(
        ...,
        description="The proposed canonical value.",
        min_length=1,
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 to 1.0.",
    )
    needs_review: bool = Field(
        ...,
        description="True if a human should review this candidate before it is used.",
    )
    reason: str = Field(
        ...,
        description="Short explanation of the candidate.",
        min_length=1,
    )

    @model_validator(mode="after")
    def low_confidence_requires_review(self) -> "AiResolutionResponse":
        """Any candidate with confidence < 0.8 must be flagged for review."""
        if self.confidence < 0.8 and not self.needs_review:
            # Don't raise — just coerce. We do this via object construction.
            # Cannot mutate frozen model, so we validate here as a check.
            raise ValueError(
                f"confidence={self.confidence} is below 0.8 but needs_review=False. "
                "Low-confidence candidates must require human review."
            )
        return self
