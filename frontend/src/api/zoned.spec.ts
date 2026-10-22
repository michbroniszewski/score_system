import { describe, expect, it } from 'vitest'
import { utcToZoned, zonedToUtc } from './zoned'

describe('zonedToUtc', () => {
  it('uses winter time (UTC+1) in November', () => {
    expect(zonedToUtc('2026-11-07T19:00', 'Europe/Warsaw')).toBe('2026-11-07T18:00:00.000Z')
  })

  it('uses summer time (UTC+2) in June', () => {
    expect(zonedToUtc('2026-06-07T19:00', 'Europe/Warsaw')).toBe('2026-06-07T17:00:00.000Z')
  })

  it('keeps a time just after midnight on its own day', () => {
    expect(zonedToUtc('2026-11-07T00:30', 'Europe/Warsaw')).toBe('2026-11-06T23:30:00.000Z')
  })
})

describe('utcToZoned', () => {
  it('shows a UTC instant as wall-clock time', () => {
    expect(utcToZoned('2026-11-06T23:30:00Z', 'Europe/Warsaw')).toBe('2026-11-07T00:30')
    expect(utcToZoned('2026-06-07T17:00:00Z', 'UTC')).toBe('2026-06-07T17:00')
  })

  it('ignores seconds a browser may add to the typed time', () => {
    expect(zonedToUtc('2026-11-06T19:00:30', 'Europe/Warsaw')).toBe('2026-11-06T18:00:00.000Z')
  })
})
