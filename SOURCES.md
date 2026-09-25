# APIx – Source Registry
#
# One row per data source considered or used.
# Update this file before enabling any live source.
#
# Columns:
#   host             – domain checked
#   robots_txt_result – allowed | disallowed | not-found (date checked)
#   tos_reviewed     – date and outcome
#   decision         – enabled | disabled (reason)

| host                   | robots_txt_result                              | tos_reviewed                       | decision                                                                                  |
|------------------------|------------------------------------------------|------------------------------------|-------------------------------------------------------------------------------------------|
| makemytrip.com         | disallowed (flight search paths) – 2026-09-20 | Not reviewed (disallowed by robots)| DISABLED – robots.txt disallows flight search paths                                       |
| book.indigoair.com     | disallowed (search + booking paths) – 2026-09-20 | Not reviewed                    | DISABLED – robots.txt disallows search and booking paths                                  |
| akasaair.com           | disallowed (implied by ToS) – 2026-09-20      | 2026-09-20 – ToS forbids copying site information without written permission | DISABLED – ToS forbids automated access      |
| easemytrip.com         | /flight-search/listing* DISALLOWED (www host) – 2026-09-25 | n/a (blocked by robots) | DISABLED on www host |
| flight.easemytrip.com  | /FlightList/Index NOT disallowed (checked 2026-09-25) | ToS not yet formally reviewed; non-commercial research use, no CAPTCHA bypass | ENABLED – scraper source code in `sources/easemytrip.py`; confirmed working in prototype2 branch |

## Decision for v1

**Live EaseMyTrip scraper is ENABLED** via `flight.easemytrip.com/FlightList/Index`.

To activate: set `source.name: easemytrip` in `config.yaml`.

Before enabling for production:
1. Formally review `flight.easemytrip.com` ToS and record date here.
2. Re-verify robots.txt allows `/FlightList/Index` for our UA.
3. Keep `min_delay_s: 8` / `max_delay_s: 15` to stay within polite crawl rates.
4. Never bypass CAPTCHA or bot-detection — stop and log if detected.
