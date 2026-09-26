class EaseMyTripSelectors:
    """Selectors for the EaseMyTrip flight search page."""
    
    ORIGIN_INPUT = "#FromSector_show"
    DESTINATION_INPUT = "#Editbox13_show"
    DATE_PICKER = "#ddate"
    SEARCH_BUTTON = ".srchBtnSe"
    
    # Results page selectors
    FLIGHT_RESULT_CARDS = ".fltResult, .nw_listing_bx"
    FARE_AMOUNT = "h4[id^='spnPrice'], [price]"
    ORIGIN_FILTER = "[og]"
    DESTINATION_FILTER = "[ds]"
