import { describe, it, expect } from 'vitest';
import { getRouteColor, CANONICAL_ROUTE_COLORS, ROUTE_PALETTE } from './palette';

describe('Route Color System (palette.ts)', () => {
  it('returns canonical colors for core routes', () => {
    expect(getRouteColor('DEL-BOM')).toBe(CANONICAL_ROUTE_COLORS['DEL-BOM']);
    expect(getRouteColor('DEL-BLR')).toBe(CANONICAL_ROUTE_COLORS['DEL-BLR']);
    expect(getRouteColor('BOM-BLR')).toBe(CANONICAL_ROUTE_COLORS['BOM-BLR']);
  });

  it('deterministically returns identical colors for repeated calls across views', () => {
    const r1 = getRouteColor('DEL-HYD');
    const r2 = getRouteColor('DEL-HYD');
    expect(r1).toBe(r2);

    const b1 = getRouteColor('BLR-DEL');
    const b2 = getRouteColor('BLR-DEL');
    expect(b1).toBe(b2);

    const c1 = getRouteColor('BOM-CCU');
    const c2 = getRouteColor('BOM-CCU');
    expect(c1).toBe(c2);
  });

  it('all palette colors are valid hex colors in ROUTE_PALETTE', () => {
    const testRoutes = ['DEL-BOM', 'DEL-HYD', 'BOM-GOI', 'BLR-PNQ', 'CCU-GAU', 'MAA-DEL', 'JAI-BOM'];
    for (const route of testRoutes) {
      const color = getRouteColor(route);
      expect(ROUTE_PALETTE).toContain(color);
      expect(color).toMatch(/^#[0-9A-F]{6}$/i);
    }
  });
});
