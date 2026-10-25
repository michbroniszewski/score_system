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

// "Kolejka 2" for a regular-season match, "Play-off, seria A, mecz 2" for a play-off game.
export function matchLabel(match: MatchOut): string {
  return match.series === null
    ? `Kolejka ${match.round}`
    : `Play-off, seria ${match.series}, mecz ${match.round}`
}

// Where a play-off team comes from: "seed 3", "winner A", "loser A" in the format file.
const SOURCE_LABELS: Record<string, string> = { winner: 'zwycięzca', loser: 'przegrany' }

export function sourceLabel(source: string): string {
  const [kind = '', name = ''] = source.split(' ')
  if (kind === 'seed') return `${name}. miejsce`
  return `${SOURCE_LABELS[kind] ?? kind} ${name}`
}

// The teams of a series not yet known: "zwycięzca A – zwycięzca D"; with more than two
// sources, the two best-seeded of them play.
export function sidesLabel(sides: string[]): string {
  const labels = sides.map(sourceLabel)
  return sides.length === 2
    ? labels.join(' – ')
    : `dwie najwyżej rozstawione drużyny z: ${labels.join(', ')}`
}

// "do 3 zwycięstw"; a single game decides "do 1 zwycięstwa".
export function winsLabel(wins: number): string {
  return wins === 1 ? 'do 1 zwycięstwa' : `do ${wins} zwycięstw`
}

// "3:1" for a played match, "W.O." for a walkover, otherwise empty.
export function score(match: MatchOut): string {
  if (match.status === 'walkover') return 'W.O.'
  if (match.status !== 'played') return ''
  const home = match.sets.filter((s) => s.home > s.away).length
  return `${home}:${match.sets.length - home}`
}
