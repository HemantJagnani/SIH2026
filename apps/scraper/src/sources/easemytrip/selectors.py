"""
EaseMyTrip Selectors for Homepage Interactive Search and Results.
"""

class EaseMyTripSelectors:
    """Selectors for the EaseMyTrip flight search and results pages."""

    # Homepage & Search Container
    HOME_FORM = "#frmHome, form#FrmEmtMdl"
    SEARCH_SECTION = ".f-search, .flt-search, #divSearchFlight"
    
    # Trip Type
    TRIP_ONE_WAY = "#Trip, input[onclick*='setType1(\\'O\\')']"
    TRIP_ROUND_TRIP = "#RTrip, input[onclick*='setType1(\\'R\\')']"
    TRIP_MULTICITY = "#MTrip, input[onclick*='setType1(\\'M\\')']"

    # Origin Selectors
    ORIGIN_TRIGGER = "#FromSector_show"
    ORIGIN_INPUT_HIDDEN = "#FromSector"
    ORIGIN_SEARCH_INPUT = "#a_FromSector_show"
    ORIGIN_DROPDOWN = "#fromautoFill"
    ORIGIN_SUGGESTION_LIST = "#fromautoFill ul.ausuggest li, #fromautoFill li"
    ORIGIN_CITY_HEAD = ".flsctrhead"

    # Destination Selectors
    DESTINATION_TRIGGER = "#Editbox13_show"
    DESTINATION_INPUT_HIDDEN = "#Editbox13"
    DESTINATION_SEARCH_INPUT = "#a_Editbox13_show"
    DESTINATION_DROPDOWN = "#toautoFill"
    DESTINATION_SUGGESTION_LIST = "#toautoFill ul.ausuggest li, #toautoFill li"
    DESTINATION_CITY_HEAD = ".flsctrhead"

    # Calendar Selectors
    DEPARTURE_DATE_TRIGGER = "#dvfarecal"
    DEPARTURE_DATE_INPUT = "#ddate"
    DATEPICKER_CONTAINER = "#dvcalendar"
    DATEPICKER_NEXT_MONTH = "#img2Nex, [onclick*='nxtMnt']"
    DATEPICKER_PREV_MONTH = "#img2Prv, [onclick*='prvtMnt']"
    DATEPICKER_MONTH_HEADER = "#dvcalendar .month2"
    DAY_DISPLAY_NO = "#ddayno"
    DAY_DISPLAY_MONTH_YEAR = "#dmonthyear"

    # Overlays & Backdrop
    BACKDROP_OVERLAY = ".overlaybg1, #overlaybg1, #overlaybgg1"

    # Passenger & Cabin
    TRAVELLER_CONTAINER = "#divTraveller, #divTravellerSelect, .flTrv"
    CABIN_SELECT = "#optClass"

    # Submission
    SEARCH_BUTTON = ".srchBtnSe, input[value='Search'].srchBtnSe, #btnSrch"

    # Results Page
    RESULTS_CONTAINER = ".listing_left, #flt-lst, .flt-res-card, .nw_listing_bx"
    SKELETON_CARD = ".nw_listing_bx.skeleton"
    REAL_FLIGHT_CARD = ".nw_listing_bx:not(.skeleton), .flt-list-item:not(.skeleton)"
    FLIGHT_RESULT_CARD = ".nw_listing_bx, .flt-list-item"
    PRICE_CONTAINER = ".flt_prc, [id^='spnPrice'], .price-text"
    AIRLINE_NAME = ".air_nmm_txt h6, .air_name"
    AIRLINE_CODE = ".air_nmm_txt span, .air_code"
    DEPARTURE_TIME = ".tm_lc, .dep_time"
    ARRIVAL_TIME = ".tmln_rc, .arr_time"
    DURATION = ".non-stp, .flt_dur"
    STOPS = ".non-stp, .stop_info"
    FARE_OPTIONS_BTN = ".air_bot_lft a, [onclick*='showMoreFare']"
    NO_FLIGHTS_CONTAINER = "#divFltNotFound, :has-text('No flights found'), :has-text('No Direct Flight')"
