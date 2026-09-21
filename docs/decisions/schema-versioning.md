# Schema Versioning

The canonical `FareObservation` model carries a `schema_version` string field
stamped on every record. This allows downstream consumers (index engine, dashboards,
analytics queries) to detect schema changes without inspecting data content.

## Current Version

`1.0.0`

## Versioning Rules

| Change Type | Action |
|---|---|
| Field removed or type changed | Bump MAJOR |
| New optional field added | Bump MINOR |
| Documentation or internal-only change | Bump PATCH |

## Approval Required (spec §47)

> **Do not change the `FareObservation` schema without explicit approval.**

Changing the schema affects:
- All historical records in PostgreSQL
- All downstream consumers (index engine, API, dashboard)
- All running adapters

## Change Log

| Version | Date | Summary |
|---|---|---|
| 1.0.0 | 2026-09-21 | Initial canonical schema from spec §13 |
