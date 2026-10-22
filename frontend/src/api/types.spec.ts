import { describe, expect, it } from 'vitest'
import openapi from '../../../backend/openapi.json'
import type * as T from './types'

// The fields of every response type the site uses. `satisfies` makes TypeScript check that
// each list names exactly the fields of the interface; the test checks them against the
// API schema snapshot, so an API change cannot silently break the site.
type Fields<X> = { [K in keyof X]-?: true }
const fields = {
  TeamRef: { id: true, name: true } satisfies Fields<T.TeamRef>,
  PlayerRef: { id: true, name: true } satisfies Fields<T.PlayerRef>,
  PresetOut: { name: true, discipline: true, sets_to_win: true, stats: true } satisfies Fields<
    T.PresetOut
  >,
  CompetitionOut: { slug: true, name: true, preset: true, timezone: true } satisfies Fields<
    T.CompetitionOut
  >,
  TeamOut: {
    id: true,
    name: true,
    short_name: true,
    club_id: true,
    saved: true,
  } satisfies Fields<T.TeamOut>,
  SetOut: { home: true, away: true } satisfies Fields<T.SetOut>,
  MatchOut: {
    id: true,
    round: true,
    home: true,
    away: true,
    status: true,
    starts_at: true,
    venue: true,
    sets: true,
    walkover_winner: true,
  } satisfies Fields<T.MatchOut>,
  StandingOut: {
    position: true,
    team: true,
    played: true,
    wins: true,
    losses: true,
    points: true,
    sets_won: true,
    sets_lost: true,
    small_points_won: true,
    small_points_lost: true,
  } satisfies Fields<T.StandingOut>,
  PlayerOut: { id: true, first_name: true, last_name: true } satisfies Fields<T.PlayerOut>,
  RosterEntryOut: {
    id: true,
    team_id: true,
    player: true,
    number: true,
    position: true,
    joined_on: true,
    left_on: true,
  } satisfies Fields<T.RosterEntryOut>,
  EventOut: {
    id: true,
    team_id: true,
    player: true,
    stat: true,
    value: true,
  } satisfies Fields<T.EventOut>,
  PlayerStatsOut: { player: true, team: true, stats: true } satisfies Fields<T.PlayerStatsOut>,
}

const schemas = openapi.components.schemas as Record<string, { properties?: object }>

describe('API types', () => {
  it.each(Object.entries(fields))('%s matches the OpenAPI schema', (name, declared) => {
    expect(Object.keys(schemas[name]?.properties ?? {}).sort()).toEqual(
      Object.keys(declared).sort(),
    )
  })

  it('MatchStatus matches the OpenAPI enum', () => {
    const statuses: Record<T.MatchStatus, true> = {
      scheduled: true,
      postponed: true,
      played: true,
      walkover: true,
      cancelled: true,
    }
    expect(openapi.components.schemas.MatchStatus.enum.sort()).toEqual(
      Object.keys(statuses).sort(),
    )
  })
})
