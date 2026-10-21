// Response bodies of API v1 used by the site (see backend/openapi.json).
// types.spec.ts checks that their fields match the schema snapshot.

export type MatchStatus = 'scheduled' | 'postponed' | 'played' | 'walkover' | 'cancelled'

export interface TeamRef {
  id: string
  name: string
}

export interface PlayerRef {
  id: string
  name: string
}

export interface PresetOut {
  name: string
  discipline: string
  sets_to_win: number
  stats: string[]
}

export interface CompetitionOut {
  slug: string
  name: string
  preset: string
  timezone: string
}

export interface TeamOut {
  id: string
  name: string
  short_name: string | null
  club_id: string | null
  saved: boolean
}

export interface SetOut {
  home: number
  away: number
}

export interface MatchOut {
  id: string
  round: number
  home: TeamRef
  away: TeamRef
  status: MatchStatus
  starts_at: string | null
  venue: string | null
  sets: SetOut[]
  walkover_winner: string | null
}

export interface StandingOut {
  position: number
  team: TeamRef
  played: number
  wins: number
  losses: number
  points: number
  sets_won: number
  sets_lost: number
  small_points_won: number
  small_points_lost: number
}

export interface PlayerOut {
  id: string
  first_name: string
  last_name: string
}

export interface RosterEntryOut {
  id: string
  team_id: string
  player: PlayerOut
  number: number | null
  position: string | null
  joined_on: string | null
  left_on: string | null
}

export interface EventOut {
  id: string
  team_id: string
  player: PlayerRef
  stat: string
  value: number
}

export interface PlayerStatsOut {
  player: PlayerRef
  team: TeamRef | null
  stats: Record<string, number>
}
