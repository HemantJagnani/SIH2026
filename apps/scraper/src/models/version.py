"""
Schema version for the canonical FareObservation model.

Every FareObservation carries this version string so that downstream
consumers can detect schema changes. Bump this version whenever the
FareObservation schema changes in a way that affects existing consumers.

Version history is tracked in: docs/decisions/schema-versioning.md

Source: spec §44 Phase 1 (schema versioning).
"""

# Current canonical schema version.
# Format: MAJOR.MINOR.PATCH
# - MAJOR: breaking change (field removed or type changed)
# - MINOR: backward-compatible addition (new optional field)
# - PATCH: documentation or internal-only change
SCHEMA_VERSION: str = "1.1.0"
