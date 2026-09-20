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
| easemytrip.com         | root robots.txt allowed (checked 2026-09-20); flight search may run on a different host | ToS not yet reviewed | PENDING – re-verify flight search host robots.txt and read ToS before enabling |

## Decision for v1

**All live sources are DISABLED.** The prototype runs on `fixture` and `synthetic` data only.

Before enabling EaseMyTrip (or any other source):
1. Fetch the exact robots.txt for the flight-search sub-host.
2. Confirm `can_fetch(USER_AGENT, search_url)` returns True.
3. Read the ToS and confirm automated non-commercial research access is permitted.
4. Record the date of both checks here.
5. Change `source.name` in `config.yaml` from `fixture` to `live`.
