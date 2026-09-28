import { describe, it, expect } from 'vitest';
import { isRunSuccess, isRunPartial, isRunFailed } from './RecordStrip';

describe('RecordStrip status helpers', () => {
  it('treats COMPLETED case-insensitively as success', () => {
    expect(isRunSuccess('COMPLETED')).toBe(true);
    expect(isRunSuccess('completed')).toBe(true);
    expect(isRunSuccess('Completed')).toBe(true);
  });

  it('treats OK and SUCCESS case-insensitively as success', () => {
    expect(isRunSuccess('OK')).toBe(true);
    expect(isRunSuccess('ok')).toBe(true);
    expect(isRunSuccess('SUCCESS')).toBe(true);
    expect(isRunSuccess('success')).toBe(true);
  });

  it('identifies partial runs correctly', () => {
    expect(isRunPartial('PARTIAL')).toBe(true);
    expect(isRunPartial('partial')).toBe(true);
    expect(isRunSuccess('partial')).toBe(false);
  });

  it('identifies failed runs correctly', () => {
    expect(isRunFailed('FAILED')).toBe(true);
    expect(isRunFailed('failed')).toBe(true);
    expect(isRunFailed('ERROR')).toBe(true);
    expect(isRunFailed('error')).toBe(true);
    expect(isRunSuccess('failed')).toBe(false);
  });

  it('handles null/undefined safely', () => {
    expect(isRunSuccess(null)).toBe(false);
    expect(isRunSuccess(undefined)).toBe(false);
    expect(isRunPartial(null)).toBe(false);
    expect(isRunFailed(null)).toBe(false);
  });
});
