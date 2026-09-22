# EaseMyTrip Fixtures

This directory contains real browser captures used to validate the `EaseMyTripParser` and the downstream pipeline (normalization -> validation -> storage).

## Important Distinction
**DO NOT use synthetic/invented fare values here.** Mock fares would only prove that the pipeline plumbing works, but wouldn't prove that our EaseMyTrip parser understands the real site's DOM structure. 

All fixtures in this directory MUST be captured from a normal Chrome session.

## Expected Files

When providing new captures, use the following structure:

- `del_bom_results.html` (Saved HTML of the results page)
- `del_bom_response.json` (Optional: If DevTools shows useful XHR/fetch responses containing the data)

## Fixture Metadata
```yaml
fixture_type: real_capture
source: easemytrip
origin: DEL
destination: BOM
```
