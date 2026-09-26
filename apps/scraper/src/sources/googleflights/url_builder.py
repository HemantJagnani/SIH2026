from datetime import date
from typing import Optional
import urllib.parse
from models.request import FareSearchRequest

class GoogleFlightsUrlBuilder:
    """
    Constructs search URLs directly for Google Flights.
    """
    
    BASE_URL = "https://www.google.com/travel/flights"
    
    @staticmethod
    def build_url(request: FareSearchRequest) -> str:
        """
        Builds the direct search URL for a Google Flights query.
        Example output: https://www.google.com/travel/flights?q=Flights%20to%20BOM%20from%20DEL%20on%202026-09-30%20oneway
        """
        origin = request.origin.upper()
        destination = request.destination.upper()
        travel_date = request.travel_date.isoformat()
        
        # We always search one-way for this POC pipeline.
        q_string = f"Flights to {destination} from {origin} on {travel_date} oneway"
        
        # Build query parameters
        params = {
            "q": q_string,
            "curr": "INR",
        }
        
        query_string = urllib.parse.urlencode(params)
        return f"{GoogleFlightsUrlBuilder.BASE_URL}?{query_string}"
