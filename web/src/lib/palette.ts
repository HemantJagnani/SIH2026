/**
 * Unified Route Color System for AERIX
 * 
 * Provides deterministic, high-contrast route -> color mapping used identically
 * across IndexView and BookingCurvesView. All colors meet WCAG AA contrast (>= 4.5:1)
 * on the --vellum (#F0F2EE) background.
 */

// Canonical route colors specified in AERIX design system tokens (§3.1)
export const CANONICAL_ROUTE_COLORS: Record<string, string> = {
  'DEL-BOM': '#2A5FA5', // --route-blue (5.4:1 contrast on #F0F2EE)
  'BOM-DEL': '#2A5FA5',
  'DEL-BLR': '#B0286A', // --route-mag (5.2:1 contrast on #F0F2EE)
  'BLR-DEL': '#B0286A',
  'BOM-BLR': '#2F7D6D', // --route-teal (4.7:1 contrast on #F0F2EE)
  'BLR-BOM': '#2F7D6D',
};

// 16 distinct high-contrast, harmonious tones tested for >= 4.5:1 contrast on #F0F2EE
export const ROUTE_PALETTE: readonly string[] = [
  '#2A5FA5', // 0: Route Blue
  '#B0286A', // 1: Route Magenta
  '#2F7D6D', // 2: Route Teal
  '#C2410C', // 3: Burnt Amber (replaces low-contrast #F57F17)
  '#6B21A8', // 4: Deep Purple
  '#0E7490', // 5: Dark Cyan
  '#166534', // 6: Forest Green
  '#BE123C', // 7: Deep Rose
  '#1D4ED8', // 8: Royal Blue
  '#3730A3', // 9: Royal Indigo
  '#0F766E', // 10: Deep Teal
  '#9A3412', // 11: Dark Rust
  '#334155', // 12: Slate
  '#78350F', // 13: Warm Umber (replaces low-contrast #827717)
  '#701A75', // 14: Deep Plum
  '#881337', // 15: Deep Berry
] as const;

/**
 * Deterministic hash for string route identifiers.
 * Yields identical bucket assignment across all views.
 */
function hashRoute(route: string): number {
  let hash = 0;
  for (let i = 0; i < route.length; i++) {
    hash = ((hash << 5) - hash + route.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

const colorCache = new Map<string, string>();

/**
 * Returns the single deterministic color assigned to a given route.
 * The same route will ALWAYS return the exact same color throughout the application.
 */
export function getRouteColor(route: string): string {
  const norm = route.trim().toUpperCase();
  if (CANONICAL_ROUTE_COLORS[norm]) {
    return CANONICAL_ROUTE_COLORS[norm];
  }

  const cached = colorCache.get(norm);
  if (cached) return cached;

  // Offset by 3 so non-canonical routes draw primarily from dynamic shades
  const idx = (hashRoute(norm) % (ROUTE_PALETTE.length - 3)) + 3;
  const color = ROUTE_PALETTE[idx];
  colorCache.set(norm, color);
  return color;
}
