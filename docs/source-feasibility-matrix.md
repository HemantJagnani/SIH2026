# Source Feasibility Matrix

| Source | Preferred access | Current assessment | Adapter |
|---|---|---|---|
| IndiGo | Official NDC | API available; authorization required | `IndigoNdcAdapter` |
| Air India | Official NDC | API available; eligibility/authorization required | `AirIndiaNdcAdapter` |
| Cleartrip | Flight API | API documented; credentials required | `CleartripFlightApiAdapter` |
| Yatra | Air API | Partner API advertised; access required | `YatraAirApiAdapter` |
| MakeMyTrip | Partner fare API if granted | Public travel-request API is not a fare-search API | API if granted; otherwise permitted web |
| Goibibo | Partner fare API if granted | Public fare-search API not confirmed | API if granted; otherwise permitted web |
| EaseMyTrip | Partner API if granted | API integrations exist; public fare-search docs not confirmed | API if granted; otherwise permitted web |
| ixigo | Partner API if granted | API services exist; public fare-search docs not confirmed | API if granted; otherwise permitted web |
| Akasa Air | Authorized API if available | Public fare-search API not confirmed | Permitted web only if authorized |
| SpiceJet | Authorized API if available | Public fare-search API not confirmed | Permitted web only if authorized |
| Air India Express | Authorized API if available | Public fare-search API not confirmed | Permitted web only if authorized |

> **Note:** This matrix is a current research snapshot and must be re-verified before production.
