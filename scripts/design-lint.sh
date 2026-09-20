#!/usr/bin/env bash
# scripts/design-lint.sh
# Fails if the frontend drifts back to generic defaults.
# Run with: bash scripts/design-lint.sh
cd "$(dirname "$0")/../web/src" || exit 1
bad=0
check() {
  if grep -RIn -E "$1" . > /dev/null 2>&1; then
    echo "FAIL: $2"; grep -RIn -E "$1" . | head -5; bad=1
  fi
}
check "linear-gradient|radial-gradient|conic-gradient"  "no gradients"
check "backdrop-filter"                                  "no glass effects"
check "box-shadow"                                       "no shadows"
check "text-transform:[[:space:]]*uppercase"             "no all-caps labels"
check "letter-spacing:[[:space:]]*0?\\.[1-9]"            "no tracked-out text"
check "border-radius:[[:space:]]*([3-9]|[1-9][0-9])px"  "radius above 2px"
check "border-radius:[[:space:]]*[0-9.]+rem"             "radius in rem"
check "curveBasis|curveCatmullRom|curveMonotone|curveCardinal|curveNatural" "no smoothed curves"
check "font-style:[[:space:]]*italic"                    "no italics"
check "className=[\"'][^\"']*\\bcard\\b"                 "no card components"
check "→|·"                                              "no arrows or middle dots in UI text"
exit $bad
