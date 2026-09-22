"""
selectors.py — IndiGo-specific Playwright locators.

All locators for the IndiGo search form and results page.
Grouped here so they can be updated in one place when the site changes
(which triggers SCHEMA_CHANGED detection rather than silent failures).

IndiGo URL: https://www.goindigo.in/

Locator strategy (spec §extraction-priority):
  1. Semantic ARIA / get_by_role / get_by_label — preferred
  2. data-testid attributes — stable identifiers
  3. Structural CSS — last resort, annotated with a warning

When selectors change, bump SELECTORS_VERSION below and file a
schema-change evidence record.

IMPORTANT: Do not add any selector that is designed to circumvent a
protection mechanism (e.g. hidden CAPTCHA fields). Only public,
user-facing search form elements belong here.
"""

# Bump this whenever any selector below changes.
SELECTORS_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

# The main booking widget root — used to confirm the page is fully loaded.
BOOKING_WIDGET = '[data-testid="booking-widget"], .booking-widget, #booking-form'

# ---------------------------------------------------------------------------
# Trip type toggle (One-Way / Round-Trip)
# ---------------------------------------------------------------------------
ONE_WAY_TAB = 'button[aria-label*="One way"], button:has-text("One Way"), label:has-text("One Way") input'
ROUND_TRIP_TAB = 'button[aria-label*="Round trip"], button:has-text("Round Trip")'

# ---------------------------------------------------------------------------
# Search form — Origin / Destination
# ---------------------------------------------------------------------------

# IndiGo uses autocomplete inputs. Filling them triggers a dropdown.
ORIGIN_INPUT = '[data-testid="origin-input"], input[placeholder*="From"], input[aria-label*="From"], input[name*="origin"]'
DESTINATION_INPUT = '[data-testid="destination-input"], input[placeholder*="To"], input[aria-label*="To"], input[name*="destination"]'

# Autocomplete suggestion dropdown — we wait for it to appear, then pick first match.
AUTOCOMPLETE_DROPDOWN = '[data-testid="autocomplete-dropdown"], .autocomplete-suggestions, ul[role="listbox"]'
AUTOCOMPLETE_FIRST_OPTION = '[data-testid="autocomplete-option"]:first-child, li[role="option"]:first-child, .suggestion-item:first-child'

# ---------------------------------------------------------------------------
# Date picker
# ---------------------------------------------------------------------------

# The departure date input or calendar trigger button.
DEPARTURE_DATE_INPUT = '[data-testid="departure-date"], input[placeholder*="Departure"], button[aria-label*="departure date"]'
# Inside the calendar, day cells — we will click the right one by text.
CALENDAR_DAY = 'button[data-date="{date}"], td[data-date="{date}"], [aria-label*="{date_label}"]'

# ---------------------------------------------------------------------------
# Passenger count
# ---------------------------------------------------------------------------

# The passenger selector button/panel trigger.
PASSENGER_SELECTOR = '[data-testid="passenger-selector"], button[aria-label*="Passengers"], .passenger-count'
ADULT_INCREASE_BTN = '[data-testid="adult-increase"], button[aria-label*="Add adult"], button:has-text("+")'

# ---------------------------------------------------------------------------
# Search submit
# ---------------------------------------------------------------------------

SEARCH_BUTTON = 'button[type="submit"], button:has-text("Search"), [data-testid="search-button"]'

# ---------------------------------------------------------------------------
# Consent / cookie banner
# ---------------------------------------------------------------------------

# Accept or dismiss the cookie consent banner if it appears.
CONSENT_ACCEPT = 'button:has-text("Accept"), button:has-text("I Accept"), [data-testid="accept-cookies"]'
CONSENT_DISMISS = 'button:has-text("Dismiss"), button:has-text("No thanks"), button[aria-label*="close" i]'

# ---------------------------------------------------------------------------
# Results page
# ---------------------------------------------------------------------------

# Container that signals the results have loaded.
RESULTS_CONTAINER = '[data-testid="flight-results"], .flight-results, .search-results, #search-results'

# Individual flight card.
FLIGHT_CARD = '[data-testid="flight-card"], .flight-card, .flight-row'

# Fields within a flight card.
PRICE_ELEMENT = '[data-testid="fare-price"], .fare-amount, .price-value, [class*="price"]'
DEPARTURE_TIME = '[data-testid="departure-time"], .departure-time, [class*="depart"]'
ARRIVAL_TIME = '[data-testid="arrival-time"], .arrival-time, [class*="arriv"]'
DURATION_ELEMENT = '[data-testid="duration"], .flight-duration, [class*="duration"]'
FLIGHT_NUMBER = '[data-testid="flight-number"], .flight-number, [class*="flightnum"]'
FARE_CLASS = '[data-testid="fare-class"], .fare-class, [class*="fareclass"]'
STOPS_ELEMENT = '[data-testid="stops"], .stops, [class*="stops"]'

# "No flights available" indicators.
NO_RESULTS_INDICATORS = [
    "no flights available",
    "no flights found",
    "sorry, no flights",
    "no results found",
    "flights not available",
]

# ---------------------------------------------------------------------------
# Network response URL patterns (for JSON extraction via page.expect_response)
# ---------------------------------------------------------------------------

# IndiGo's search API endpoint pattern — the browser calls this when results load.
# We capture this response to prefer structured JSON over DOM parsing.
SEARCH_API_URL_PATTERN = "/api/flight/search, /search-result, /availability"
