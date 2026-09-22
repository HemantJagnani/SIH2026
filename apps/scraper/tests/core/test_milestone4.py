"""
test_milestone4.py — Unit tests for Milestone 4 (IndiGo adapter).

All tests are offline. Browser-dependent components (navigation, full adapter)
are not tested here — they require a real browser and are validated manually.

What IS tested here:
  - parser.py: extract_from_network_response with mock JSON payloads

Run with:
    pytest apps/scraper/tests/core/test_milestone4.py -v
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from sources.airlines.indigo.parser import extract_from_network_response


# ===========================================================================
# parser.py — extract_from_network_response
# ===========================================================================

class TestExtractFromNetworkResponse:

    @pytest.mark.asyncio
    async def test_standard_response_shape(self):
        """Typical IndiGo API response shape."""
        json_data = {
            "data": {
                "flights": [
                    {
                        "flightNumber": "6E 123",
                        "departureTime": "06:30",
                        "arrivalTime": "08:45",
                        "stops": 0,
                        "totalFare": 5499,
                        "currency": "INR",
                        "offerId": "offer-abc",
                    },
                    {
                        "flightNumber": "6E 456",
                        "departureTime": "09:00",
                        "arrivalTime": "11:15",
                        "stops": 0,
                        "totalFare": 6199,
                        "currency": "INR",
                    },
                ]
            }
        }
        fares = await extract_from_network_response(json_data)
        assert len(fares) == 2
        assert fares[0]["flight_number"] == "6E 123"
        assert fares[0]["total_fare"] == 5499

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty(self):
        assert await extract_from_network_response({}) == []

    @pytest.mark.asyncio
    async def test_none_returns_empty(self):
        assert await extract_from_network_response(None) == []

    @pytest.mark.asyncio
    async def test_alternative_key_paths(self):
        """Parser should handle alternate key names in the JSON."""
        json_data = {
            "flights": [
                {
                    "number": "6E 789",
                    "departs": "14:00",
                    "arrives": "16:30",
                    "price": 7299,
                    "currency": "INR",
                }
            ]
        }
        fares = await extract_from_network_response(json_data)
        assert len(fares) == 1
        assert fares[0]["total_fare"] == 7299

    @pytest.mark.asyncio
    async def test_raw_key_preserved(self):
        """The _raw key should contain the original item for audit."""
        json_data = {
            "data": {
                "flights": [{"flightNumber": "6E-001", "totalFare": 3999}]
            }
        }
        fares = await extract_from_network_response(json_data)
        assert "_raw" in fares[0]
        assert fares[0]["_raw"]["flightNumber"] == "6E-001"
