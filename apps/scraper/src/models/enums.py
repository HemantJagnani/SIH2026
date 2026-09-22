"""
Enums for the India Airfare Price Index pipeline.

Defined per spec §12 (Collection status), §13 (FareObservation fields),
§40 (Collection lifecycle), §6 (Collection mode), and Phase 9 (browser
collection workflow states and extended blocking/failure taxonomy).

All enums are string-based for JSON serialization compatibility with
PostgreSQL and Pydantic models.
"""

from enum import Enum


# ---------------------------------------------------------------------------
# §12 – Collection Status
# Every collection job must result in one of these explicit statuses.
# Do not turn every failure into price = NULL.
# ---------------------------------------------------------------------------

class CollectionStatus(str, Enum):
    """
    Explicit outcome status for every collection job attempt.
    Source: spec §12.
    """
    SUCCESS = "SUCCESS"
    NO_RESULTS = "NO_RESULTS"
    SOLD_OUT = "SOLD_OUT"
    NOT_FOUND = "NOT_FOUND"
    SOURCE_ERROR = "SOURCE_ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    ACCESS_RESTRICTED = "ACCESS_RESTRICTED"
    CAPTCHA_PRESENT = "CAPTCHA_PRESENT"
    PARSER_ERROR = "PARSER_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NORMALIZATION_ERROR = "NORMALIZATION_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# ---------------------------------------------------------------------------
# §6 – Collection Mode
# How data was collected from the source.
# ---------------------------------------------------------------------------

class CollectionMode(str, Enum):
    """
    Mechanism used to collect data from a source.
    Source: spec §6.
    """
    API = "API"
    HTTP = "HTTP"
    BROWSER = "BROWSER"


# ---------------------------------------------------------------------------
# §6 / §13 – Trip Type
# ---------------------------------------------------------------------------

class TripType(str, Enum):
    """
    One-way or round-trip itinerary type.
    Source: spec §6, §13.
    """
    ONE_WAY = "ONE_WAY"
    ROUND_TRIP = "ROUND_TRIP"


# ---------------------------------------------------------------------------
# §13 – Cabin Class
# ---------------------------------------------------------------------------

class CabinClass(str, Enum):
    """
    Cabin class of the fare offer.
    Source: spec §13.
    """
    ECONOMY = "ECONOMY"
    PREMIUM_ECONOMY = "PREMIUM_ECONOMY"
    BUSINESS = "BUSINESS"
    FIRST = "FIRST"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# §13 – Availability Status
# IMPORTANT: Never interpret SOLD_OUT as zero price.
# ---------------------------------------------------------------------------

class AvailabilityStatus(str, Enum):
    """
    Seat availability status for a given fare observation.
    Source: spec §13; extended in Phase 9 to cover all browser-scraper
    failure and blocking states.

    WARNING: SOLD_OUT is not the same as price=0. Never equate the two.
    Every non-AVAILABLE state must be stored with a reason; never silently
    dropped.
    """
    # --- Happy-path ---
    AVAILABLE = "AVAILABLE"

    # --- No-inventory states ---
    NO_RESULTS = "NO_RESULTS"         # Search returned, but no flights found
    SOLD_OUT = "SOLD_OUT"             # Flight exists but fully sold out

    # --- Access / policy blocks (do NOT retry or rotate after these) ---
    CAPTCHA_BLOCKED = "CAPTCHA_BLOCKED"       # CAPTCHA page detected
    ACCESS_BLOCKED = "ACCESS_BLOCKED"         # 403 or hard IP block
    RATE_LIMITED = "RATE_LIMITED"             # 429 received
    AUTH_REQUIRED = "AUTH_REQUIRED"           # Login wall encountered (401)
    ROBOTS_DISALLOWED = "ROBOTS_DISALLOWED"   # robots.txt forbids this path
    LEGAL_RESTRICTION = "LEGAL_RESTRICTION"   # 451 or explicit ToS block

    # --- Search / parser failures ---
    SEARCH_ERROR = "SEARCH_ERROR"             # Error during the search itself
    SCHEMA_CHANGED = "SCHEMA_CHANGED"         # DOM/API structure no longer matches parser
    INVALID = "INVALID"                       # Observation failed validation gate

    # --- Server / transport failures ---
    SERVER_ERROR = "SERVER_ERROR"             # 5xx from the source

    # --- Legacy / catch-all (kept for backward compatibility) ---
    NOT_FOUND = "NOT_FOUND"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# §40 – Collection Job Lifecycle Status
# Full happy path AND failure paths are represented.
# ---------------------------------------------------------------------------

class JobLifecycleStatus(str, Enum):
    """
    Lifecycle state of a collection job, from creation to publication.
    Source: spec §40.

    Happy path:
        CREATED → QUEUED → RUNNING → SOURCE_RESPONSE → EXTRACTED
        → NORMALIZED → VALIDATED → QUALITY_CHECKED → PUBLISHED

    Failure paths:
        RUNNING → FAILED | RESTRICTED | TIMEOUT
        EXTRACTED → NORMALIZATION_EXCEPTION → AI_FALLBACK
                 → RESOLVED | QUARANTINED
    """
    # Happy path
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SOURCE_RESPONSE = "SOURCE_RESPONSE"
    EXTRACTED = "EXTRACTED"
    NORMALIZED = "NORMALIZED"
    VALIDATED = "VALIDATED"
    QUALITY_CHECKED = "QUALITY_CHECKED"
    PUBLISHED = "PUBLISHED"

    # Runtime failure paths
    FAILED = "FAILED"
    RESTRICTED = "RESTRICTED"
    TIMEOUT = "TIMEOUT"

    # Normalization / AI exception paths
    NORMALIZATION_EXCEPTION = "NORMALIZATION_EXCEPTION"
    AI_FALLBACK = "AI_FALLBACK"
    RESOLVED = "RESOLVED"
    QUARANTINED = "QUARANTINED"


# ---------------------------------------------------------------------------
# Phase 9 – Browser Workflow State Machine
# Each browser collection job steps through these states in sequence.
# On any blocking failure the state machine halts; it never skips states
# or silently retries a blocked source.
# ---------------------------------------------------------------------------

class WorkflowState(str, Enum):
    """
    Fine-grained state for a single browser-based search job.
    Source: Phase 9 spec §State-machine.

    Transitions:
        CREATED
         → POLICY_CHECK
         → OPEN_SOURCE
         → WAIT_PAGE_READY
         → HANDLE_CONSENT
         → ENTER_ORIGIN
         → ENTER_DESTINATION
         → SELECT_DATE
         → SELECT_PASSENGERS
         → SUBMIT_SEARCH
         → WAIT_RESULT_STATE
         → EXTRACT
         → VALIDATE
         → PERSIST
         → DONE

    Terminal failure states (no further transitions):
        ROBOTS_DISALLOWED, CAPTCHA_BLOCKED, ACCESS_BLOCKED,
        RATE_LIMITED, AUTH_REQUIRED, NO_RESULTS, SOLD_OUT,
        SEARCH_ERROR, SCHEMA_CHANGED, INVALID
    """
    # Normal progression
    CREATED = "CREATED"
    POLICY_CHECK = "POLICY_CHECK"
    OPEN_SOURCE = "OPEN_SOURCE"
    WAIT_PAGE_READY = "WAIT_PAGE_READY"
    HANDLE_CONSENT = "HANDLE_CONSENT"
    ENTER_ORIGIN = "ENTER_ORIGIN"
    ENTER_DESTINATION = "ENTER_DESTINATION"
    SELECT_DATE = "SELECT_DATE"
    SELECT_PASSENGERS = "SELECT_PASSENGERS"
    SUBMIT_SEARCH = "SUBMIT_SEARCH"
    WAIT_RESULT_STATE = "WAIT_RESULT_STATE"
    EXTRACT = "EXTRACT"
    VALIDATE = "VALIDATE"
    PERSIST = "PERSIST"
    DONE = "DONE"

    # Terminal failure states
    ROBOTS_DISALLOWED = "ROBOTS_DISALLOWED"
    CAPTCHA_BLOCKED = "CAPTCHA_BLOCKED"
    ACCESS_BLOCKED = "ACCESS_BLOCKED"
    RATE_LIMITED = "RATE_LIMITED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    NO_RESULTS = "NO_RESULTS"
    SOLD_OUT = "SOLD_OUT"
    SEARCH_ERROR = "SEARCH_ERROR"
    SCHEMA_CHANGED = "SCHEMA_CHANGED"
    INVALID = "INVALID"
