import type { MatchOut, MatchStatus } from './types'

// Dates come in UTC; matches are shown in the competition's time zone.
export function formatStart(startsAt: string | null, timeZone: string): string {
  if (startsAt === null) return 'termin do ustalenia'
  return new Intl.DateTimeFormat('pl-PL', {
    timeZone,
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(startsAt))
}

export const STATUS_LABELS: Record<MatchStatus, string> = {
  scheduled: 'zaplanowany',
  postponed: 'przełożony',
  played: 'rozegrany',
  walkover: 'walkower',
  cancelled: 'odwołany',
}

// Statistic codes come from the discipline preset; unknown codes are shown as they are.
const STAT_LABELS: Record<string, string> = {
  points_scored: 'Punkty',
  aces: 'Asy',
  blocks: 'Bloki',
  mvp: 'MVP',
}

export function statLabel(code: string): string {
  return STAT_LABELS[code] ?? code
}

// "3:1" for a played match, "W.O." for a walkover, otherwise empty.
export function score(match: MatchOut): string {
  if (match.status === 'walkover') return 'W.O.'
  if (match.status !== 'played') return ''
  const home = match.sets.filter((s) => s.home > s.away).length
  return `${home}:${match.sets.length - home}`
}
