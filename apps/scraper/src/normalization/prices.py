"""
Price normalizer.

Parses strings like "₹5,240", "INR 5,240", "5240" into Decimal.
"""

import re
from decimal import Decimal, InvalidOperation

from normalization.core import NormalizationException, NormalizationResult


def normalize_price(raw_price: str, field_name: str = "price") -> NormalizationResult[Decimal]:
    """
    Deterministically parses a currency string into a Decimal.
    Assumes INR as the currency base unless it specifies otherwise (which we reject).
    
    Args:
        raw_price: The raw price string from the source (e.g., "₹ 5,240.00")
        field_name: The name of the field being normalized (for exception context)
        
    Returns:
        NormalizationResult[Decimal]
        
    Raises:
        NormalizationException: If the price cannot be deterministically parsed.
    """
    if not raw_price or not raw_price.strip():
        raise NormalizationException(field_name, raw_price, "Empty price string")

    # Clean the string
    cleaned = raw_price.strip().upper()

    # Reject explicitly non-INR prices to prevent silent conversion errors
    if "USD" in cleaned or "$" in cleaned or "EUR" in cleaned or "£" in cleaned or "AED" in cleaned:
        raise NormalizationException(field_name, raw_price, "Non-INR currency detected")

    # Remove known INR symbols and text
    cleaned = re.sub(r'(?:₹|INR|RS\.?|RUPEES)\s*', '', cleaned)
    
    # Remove whitespace and commas
    cleaned = re.sub(r'[\s,]', '', cleaned)

    if not cleaned:
        raise NormalizationException(field_name, raw_price, "No numerical digits found")

    try:
        val = Decimal(cleaned)
        if val < 0:
            raise NormalizationException(field_name, raw_price, "Negative price not allowed")
            
        return NormalizationResult(
            raw_value=raw_price,
            normalized_value=val,
            is_success=True,
            confidence=1.0,
        )
    except InvalidOperation:
        raise NormalizationException(field_name, raw_price, "Invalid decimal format")
