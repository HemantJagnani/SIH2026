"""
Entity Mapper for Airlines and Airports.

Uses a cached version of the entity_mappings database table to resolve
raw source strings into canonical entities deterministically.
"""

from typing import Any

from sqlalchemy import select

from normalization.core import NormalizationException, NormalizationResult
from storage.models import EntityMapping
from storage.postgres import DatabaseClient


class EntityMapper:
    """
    In-memory cache for entity mappings (Airlines, Airports).
    Refreshed periodically or at job start.
    """
    def __init__(self):
        # Dict structure: {entity_type: {source: {raw_value: canonical_value}}}
        self._cache: dict[str, dict[str, dict[str, str]]] = {}
        self._is_loaded = False

    async def load(self, db_client: DatabaseClient) -> None:
        """Loads all APPROVED entity mappings into memory."""
        self._cache.clear()
        
        async with db_client.session() as session:
            # Load only approved mappings
            stmt = select(EntityMapping).where(EntityMapping.approval_status == "APPROVED")
            result = await session.execute(stmt)
            mappings = result.scalars().all()
            
            for m in mappings:
                if m.entity_type not in self._cache:
                    self._cache[m.entity_type] = {}
                if m.source not in self._cache[m.entity_type]:
                    self._cache[m.entity_type][m.source] = {}
                    
                # Store exact match lowercased for deterministic lookup
                self._cache[m.entity_type][m.source][m.raw_value.lower()] = m.canonical_value

        self._is_loaded = True

    def _normalize(self, entity_type: str, source: str, raw_value: str, field_name: str) -> NormalizationResult[str]:
        if not self._is_loaded:
            raise RuntimeError("EntityMapper not loaded. Call await load(db_client) first.")
            
        if not raw_value or not raw_value.strip():
            raise NormalizationException(field_name, raw_value, f"Empty {entity_type} string")
            
        cleaned = raw_value.strip().lower()
        
        # Try source-specific exact match
        source_map = self._cache.get(entity_type, {}).get(source, {})
        if cleaned in source_map:
            return NormalizationResult(
                raw_value=raw_value,
                normalized_value=source_map[cleaned],
                is_success=True,
                confidence=1.0,
            )
            
        # Try global fallback match (source = "GLOBAL")
        global_map = self._cache.get(entity_type, {}).get("GLOBAL", {})
        if cleaned in global_map:
            return NormalizationResult(
                raw_value=raw_value,
                normalized_value=global_map[cleaned],
                is_success=True,
                confidence=1.0,
            )
            
        raise NormalizationException(field_name, raw_value, f"No deterministic mapping found for {entity_type}")

    def normalize_airline(self, source: str, raw_airline: str) -> NormalizationResult[str]:
        return self._normalize("AIRLINE", source, raw_airline, "airline")

    def normalize_airport(self, source: str, raw_airport: str) -> NormalizationResult[str]:
        return self._normalize("AIRPORT", source, raw_airport, "airport")

# Global singleton instance for use by parsers
entity_mapper = EntityMapper()


import re

def normalize_flight_number(raw: str, field_name: str = "flight_number") -> NormalizationResult[str]:
    """
    Normalize a flight number string. E.g. "6E 123" → "6E-123".
    """
    if not raw or not raw.strip():
        raise NormalizationException(field_name, raw, "Empty flight number string")
        
    normalized = re.sub(r"([A-Z0-9]{2})\s+([0-9]+)", r"\1-\2", raw.strip().upper())
    
    if not normalized:
        raise NormalizationException(field_name, raw, "Could not normalize flight number")
        
    return NormalizationResult(
        raw_value=raw,
        normalized_value=normalized,
        is_success=True,
        confidence=1.0,
    )

