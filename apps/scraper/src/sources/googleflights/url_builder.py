from datetime import date
from typing import Optional, Dict
import urllib.parse
from models.request import FareSearchRequest

class GoogleFlightsUrlBuilder:
    """
    Constructs search URLs directly for Google Flights.
    """
    
    BASE_URL = "https://www.google.com/travel/flights"

    # Destination entity resolution dictionary for Google Flights natural-language queries.
    # While standard 3-letter IATA airport codes (DEL, BOM, BLR, etc.) resolve natively,
    # bare 'GAU' is not recognized as a destination entity by Google Flights' NLP query
    # parser and triggers fallback to the generic Explore page.
    # Mapping GAU -> "Guwahati" ensures deterministic resolution to Lokpriya Gopinath Bordoloi Airport.
    DESTINATION_ENTITY_MAP: Dict[str, str] = {
        "GAU": "Guwahati",
    }

    @classmethod
    def resolve_destination(cls, destination: str) -> str:
        """
        Resolves destination code to a Google Flights-compatible entity string.
        Returns the mapped entity name if defined (e.g. 'GAU' -> 'Guwahati'),
        otherwise preserves the uppercase IATA code.
        """
        dest_clean = destination.strip().upper()
        return cls.DESTINATION_ENTITY_MAP.get(dest_clean, dest_clean)
    
    @classmethod
    def build_url(cls, request: FareSearchRequest) -> str:
        """
        Builds the direct search URL for a Google Flights query.
        Example output: https://www.google.com/travel/flights?q=Flights%20to%20BOM%20from%20DEL%20on%202026-09-30%20oneway
        """
        origin = request.origin.upper()
        destination = cls.resolve_destination(request.destination)
        travel_date = request.travel_date.isoformat()
        
        # We always search one-way for this POC pipeline.
        q_string = f"Flights to {destination} from {origin} on {travel_date} oneway"
        
        # Build query parameters
        params = {
            "q": q_string,
            "curr": "INR",
        }
        
        query_string = urllib.parse.urlencode(params)
        return f"{cls.BASE_URL}?{query_string}"
