import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import App from './App.vue'
import { routes } from './router'

const eagles = { id: 't1', name: 'Eagles' }
const owls = { id: 't2', name: 'Owls' }
const played = {
  id: 'm1',
  round: 1,
  home: eagles,
  away: owls,
  status: 'played',
  starts_at: '2026-11-06T18:00:00Z',
  venue: 'City Hall',
  sets: [
    { home: 25, away: 20 },
    { home: 25, away: 18 },
    { home: 25, away: 22 },
  ],
  walkover_winner: null,
}
const scheduled = { ...played, id: 'm2', round: 2, status: 'scheduled', sets: [], venue: null }

// API responses by path, as the live API or the snapshot would answer them.
const responses: Record<string, unknown> = {
  '/api/v1/competitions': [
    { slug: 'league', name: 'City League', preset: 'volleyball', timezone: 'Europe/Warsaw' },
  ],
  '/api/v1/competitions/league': {
    slug: 'league',
    name: 'City League',
    preset: 'volleyball',
    timezone: 'Europe/Warsaw',
  },
  '/api/v1/competitions/league/standings': [
    { position: 1, team: eagles, played: 1, wins: 1, losses: 0, points: 3 },
    { position: 2, team: owls, played: 1, wins: 0, losses: 1, points: 0 },
  ].map((row) => ({
    ...row,
    sets_won: 3,
    sets_lost: 0,
    small_points_won: 75,
    small_points_lost: 60,
  })),
  '/api/v1/competitions/league/matches': [played, scheduled],
  '/api/v1/competitions/league/teams': [
    { ...eagles, short_name: null, club_id: null, saved: false },
    { ...owls, short_name: null, club_id: null, saved: false },
  ],
  '/api/v1/competitions/league/teams/t1/roster': [
    {
      id: 'e1',
      team_id: 't1',
      player: { id: 'p1', first_name: 'Anna', last_name: 'Nowak' },
      number: 7,
      position: 'setter',
      joined_on: null,
      left_on: null,
    },
    {
      id: 'e2',
      team_id: 't1',
      player: { id: 'p2', first_name: 'Ola', last_name: 'Kowal' },
      number: 3,
      position: null,
      joined_on: null,
      left_on: '2026-10-01',
    },
  ],
  '/api/v1/competitions/league/stats': [
    {
      player: { id: 'p1', name: 'Anna Nowak' },
      team: eagles,
      stats: { points_scored: 12, aces: 2, blocks: 0, mvp: 1 },
    },
  ],
  '/api/v1/matches/m1': played,
  '/api/v1/matches/m1/events': [
    { id: 'ev1', team_id: 't1', player: { id: 'p1', name: 'Anna Nowak' }, stat: 'aces', value: 2 },
  ],
}

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) =>
      url in responses
        ? new Response(JSON.stringify(responses[url]))
        : new Response('', { status: 404 }),
    ),
  )
})

afterEach(() => vi.unstubAllGlobals())

async function open(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push(path)
  const wrapper = mount(App, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('public site', () => {
  it('lists competitions', async () => {
    const page = await open('/')

    expect(page.text()).toContain('City League')
  })

  it('shows the standings table', async () => {
    const page = await open('/competitions/league')

    const rows = page.findAll('tbody tr').map((row) => row.text())
    expect(rows[0]).toMatch(/^1\s*Eagles.*3:0/)
    expect(rows[1]).toContain('Owls')
  })

  it('groups fixtures by round, with results and Warsaw time', async () => {
    const page = await open('/competitions/league/matches')

    expect(page.findAll('h2').map((h) => h.text())).toEqual(['Kolejka 1', 'Kolejka 2'])
    expect(page.text()).toContain('3:0')
    expect(page.text()).toContain('19:00') // 18:00 UTC in Warsaw (winter time)
    expect(page.text()).toContain('City Hall')
  })

  it('shows a match with its sets and statistics', async () => {
    const page = await open('/competitions/league/matches/m1')

    expect(page.text()).toContain('Set 1: 25:20')
    expect(page.text()).toContain('Anna Nowak: Asy 2')
  })

  it('shows the current roster and past players', async () => {
    const page = await open('/competitions/league/teams/t1')

    expect(page.find('h2').text()).toBe('Eagles')
    expect(page.find('tbody').text()).toContain('Anna Nowak')
    expect(page.find('tbody').text()).not.toContain('Ola Kowal')
    expect(page.text()).toContain('Ola Kowal (do 2026-10-01)')
  })

  it('shows player statistics with the preset columns', async () => {
    const page = await open('/competitions/league/stats')

    expect(page.findAll('th').map((th) => th.text())).toEqual([
      'Zawodnik',
      'Drużyna',
      'Punkty',
      'Asy',
      'Bloki',
      'MVP',
    ])
    expect(page.find('tbody').text()).toMatch(/Anna Nowak\s*Eagles\s*12\s*2\s*0\s*1/)
  })

  it('says when data cannot be loaded', async () => {
    const page = await open('/competitions/missing')

    expect(page.text()).toContain('Nie udało się wczytać danych.')
  })
})
