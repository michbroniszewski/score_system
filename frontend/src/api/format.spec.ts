import { describe, expect, it } from 'vitest'
import { formatStart, matchLabel, score, sidesLabel, statLabel, winsLabel } from './format'
import type { MatchOut } from './types'

const match: MatchOut = {
  id: 'm1',
  round: 1,
  home: { id: 'h', name: 'Eagles' },
  away: { id: 'a', name: 'Owls' },
  status: 'played',
  starts_at: '2026-11-06T23:30:00Z',
  venue: null,
  sets: [
    { home: 25, away: 20 },
    { home: 20, away: 25 },
    { home: 25, away: 20 },
    { home: 25, away: 23 },
  ],
  walkover_winner: null,
  series: null,
}

describe('formatStart', () => {
  it('shows the time in the competition time zone', () => {
    // 23:30 UTC on 6 November is 00:30 on 7 November in Warsaw.
    expect(formatStart(match.starts_at, 'Europe/Warsaw')).toMatch(/7 lis.*00:30/)
  })

  it('says when there is no date yet', () => {
    expect(formatStart(null, 'Europe/Warsaw')).toBe('termin do ustalenia')
  })
})

describe('score', () => {
  it('counts sets of a played match', () => {
    expect(score(match)).toBe('3:1')
  })

  it('marks a walkover and leaves other matches empty', () => {
    expect(score({ ...match, status: 'walkover', sets: [] })).toBe('W.O.')
    expect(score({ ...match, status: 'scheduled', sets: [] })).toBe('')
  })
})

describe('statLabel', () => {
  it('translates known statistics and keeps unknown codes', () => {
    expect(statLabel('aces')).toBe('Asy')
    expect(statLabel('goals')).toBe('goals')
  })
})

describe('play-off labels', () => {
  it('names a play-off game by its series', () => {
    expect(matchLabel(match)).toBe('Kolejka 1')
    expect(matchLabel({ ...match, series: 'A', round: 2 })).toBe('Play-off, seria A, mecz 2')
  })

  it('says how many wins a series needs', () => {
    expect(winsLabel(1)).toBe('do 1 zwycięstwa')
    expect(winsLabel(3)).toBe('do 3 zwycięstw')
  })

  it('describes where the teams of a series come from', () => {
    expect(sidesLabel(['seed 1', 'seed 8'])).toBe('1. miejsce – 8. miejsce')
    expect(sidesLabel(['winner A', 'winner D'])).toBe('zwycięzca A – zwycięzca D')
    expect(sidesLabel(['loser A', 'loser B', 'loser C'])).toBe(
      'dwie najwyżej rozstawione drużyny z: przegrany A, przegrany B, przegrany C',
    )
  })
})
