"""
Google Flights DOM Selectors.

Prioritizing structural, accessibility, and ARIA attributes over obfuscated classes.
"""

class GoogleFlightsSelectors:
    # Consent / GDPR overlays
    CONSENT_FORM = 'form[action*="consent.google.com"]'
    CONSENT_ACCEPT_BUTTON = 'button:has-text("Accept all"), button:has-text("I agree")'

    # Result state detection
    RESULTS_CONTAINER = '[role="main"]'
    NO_RESULTS_INDICATOR = 'text="No matching flights found", text="No flights found"'
    CAPTCHA_INDICATOR = 'form[action*="CaptchaRedirect"], #captcha-form'

    # Flight Result Cards
    # Google separates into "Best" and "Other" flights, usually in list items
    FLIGHT_LIST = 'ul'
    FLIGHT_CARD_ITEM = 'li'
    
    # We look for cards that have semantic flight info
    # E.g. finding elements by ARIA labels or standard structural tags.
    # Instead of specific classes, the parser will use beautifulsoup to find spans 
    # with text matching time/price formats.

    # Details Panel
    EXPAND_CARD_BUTTON = 'button[aria-expanded="false"]' # Click this to expand
    DETAILS_PANEL = '[role="region"]' # Once expanded
    SEGMENT_ROW = 'div:has(> div > span:has-text("Flight"))' # e.g., Flight 6E 123
    BAGGAGE_INFO = 'span:has-text("baggage"), span:has-text("Carry-on")'
    FARE_FAMILY_BUTTON = 'button:has-text("Select")'
    FARE_OPTIONS_MODAL = '[role="dialog"]'
    SCARCITY_INDICATOR = 'span:has-text("left at this price")'
