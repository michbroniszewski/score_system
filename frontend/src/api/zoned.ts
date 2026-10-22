// Conversion between UTC instants (the API) and wall-clock times in a time zone (the
// <input type="datetime-local"> value "2026-11-07T19:00" a person types).

function offsetMs(instant: number, timeZone: string): number {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    hourCycle: 'h23',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).formatToParts(instant)
  const get = (type: string) => Number(parts.find((p) => p.type === type)?.value)
  const asUtc = Date.UTC(
    get('year'),
    get('month') - 1,
    get('day'),
    get('hour'),
    get('minute'),
    get('second'),
  )
  return asUtc - Math.floor(instant / 1000) * 1000
}

// "2026-11-07T19:00" in `timeZone` -> "2026-11-07T18:00:00.000Z" (seconds are dropped).
export function zonedToUtc(local: string, timeZone: string): string {
  // The wall-clock fields read as if they were UTC.
  const wall = Date.parse(`${local.slice(0, 16)}:00Z`)
  // The offset depends on the instant (summer time), so correct once with the first guess.
  const first = wall - offsetMs(wall, timeZone)
  return new Date(wall - offsetMs(first, timeZone)).toISOString()
}

// "2026-11-07T18:00:00Z" -> "2026-11-07T19:00" in `timeZone`.
export function utcToZoned(utc: string, timeZone: string): string {
  const instant = Date.parse(utc)
  return new Date(instant + offsetMs(instant, timeZone)).toISOString().slice(0, 16)
}
