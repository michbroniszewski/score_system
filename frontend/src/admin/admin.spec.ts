import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import App from '../App.vue'
import { routes } from '../router'

const eagles = { id: 't1', name: 'Eagles' }
const owls = { id: 't2', name: 'Owls' }
const league = { slug: 'league', name: 'City League', preset: 'volleyball', timezone: 'Europe/Warsaw' }
const scheduled = {
  id: 'm1',
  round: 1,
  home: eagles,
  away: owls,
  status: 'scheduled',
  starts_at: null,
  venue: null,
  sets: [],
  walkover_winner: null,
}
const anna = {
  id: 'e1',
  team_id: 't1',
  player: { id: 'p1', first_name: 'Anna', last_name: 'Nowak' },
  number: 7,
  position: null,
  joined_on: null,
  left_on: null,
}
const team = (t: { id: string; name: string }) => ({ ...t, short_name: null, club_id: null, saved: false })

let responses: Record<string, unknown>
let sent: { method: string; url: string; body: unknown }[]

beforeEach(() => {
  responses = {
    'GET /api/v1/competitions': [league],
    'GET /api/v1/presets': ['volleyball'],
    'GET /api/v1/presets/volleyball': {
      name: 'volleyball',
      discipline: 'volleyball',
      sets_to_win: 3,
      stats: ['points_scored', 'aces'],
    },
    'GET /api/v1/competitions/league': league,
    'GET /api/v1/competitions/league/teams': [team(eagles), team(owls)],
    'GET /api/v1/competitions/league/matches': [],
    'GET /api/v1/teams': [],
    'GET /api/v1/matches/m1': scheduled,
    'GET /api/v1/matches/m1/events': [],
    'GET /api/v1/competitions/league/teams/t1/roster': [anna],
    'GET /api/v1/competitions/league/teams/t2/roster': [],
  }
  sent = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      if (method !== 'GET') sent.push({ method, url, body: init?.body && JSON.parse(String(init.body)) })
      const key = `${method} ${url}`
      if (!(key in responses)) return new Response('', { status: 404 })
      const body = responses[key]
      return body instanceof Response ? body : new Response(JSON.stringify(body ?? {}))
    }),
  )
})

afterEach(() => vi.unstubAllGlobals())

async function open(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push(path)
  const wrapper = mount(App, { global: { plugins: [router] } })
  await flushPromises()
  return { page: wrapper, router }
}

describe('admin panel', () => {
  it('creates a competition and opens it', async () => {
    responses['POST /api/v1/competitions'] = league
    const { page, router } = await open('/admin')

    const [name, slug] = page.findAll('input')
    await name!.setValue('City League')
    await slug!.setValue('league')
    await page.find('form').trigger('submit')
    await flushPromises()

    expect(sent).toEqual([
      {
        method: 'POST',
        url: '/api/v1/competitions',
        body: { name: 'City League', slug: 'league', preset: 'volleyball', timezone: 'Europe/Warsaw' },
      },
    ])
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('admin-competition'))
  })

  it('enters a new team into a competition', async () => {
    responses['POST /api/v1/competitions/league/teams'] = team({ id: 't3', name: 'Hawks' })
    const { page } = await open('/admin/competitions/league')

    await page.find('form input:not([type])').setValue('Hawks')
    await page.find('form').trigger('submit')
    await flushPromises()

    expect(sent[0]).toEqual({
      method: 'POST',
      url: '/api/v1/competitions/league/teams',
      body: { team: { name: 'Hawks', saved: false } },
    })
  })

  it('reschedules a match in the competition time zone', async () => {
    responses['POST /api/v1/matches/m1/reschedule'] = scheduled
    const { page } = await open('/admin/competitions/league/matches/m1')

    await page.find('input[type="datetime-local"]').setValue('2026-11-06T19:00')
    await page.findAll('form')[0]!.trigger('submit')
    await flushPromises()

    expect(sent[0]).toEqual({
      method: 'POST',
      url: '/api/v1/matches/m1/reschedule',
      body: { starts_at: '2026-11-06T18:00:00.000Z', venue: null },
    })
  })

  it('records the filled sets and shows a rejection', async () => {
    responses['POST /api/v1/matches/m1/result'] = new Response(
      JSON.stringify({ detail: 'the winner must take 3 sets' }),
      { status: 422 },
    )
    const { page } = await open('/admin/competitions/league/matches/m1')

    const inputs = page.findAll('.set-row input')
    expect(inputs).toHaveLength(6) // sets_to_win rows to start with
    for (const [i, value] of [25, 20, 25, 18].entries()) await inputs[i]!.setValue(value)
    await page.findAll('form')[1]!.trigger('submit')
    await flushPromises()

    expect(sent[0]!.body).toEqual({
      sets: [
        { home: 25, away: 20 },
        { home: 25, away: 18 },
      ],
    })
    expect(page.text()).toContain('the winner must take 3 sets')
  })

  it('adds a statistic for a player of a played match', async () => {
    responses['GET /api/v1/matches/m1'] = { ...scheduled, status: 'played', sets: [{ home: 25, away: 20 }] }
    responses['POST /api/v1/matches/m1/events'] = {}
    const { page } = await open('/admin/competitions/league/matches/m1')

    const form = page.findAll('form').at(-1)!
    const [teamSelect, playerSelect, statSelect] = form.findAll('select')
    await teamSelect!.setValue('t1')
    await playerSelect!.setValue('p1')
    await statSelect!.setValue('aces')
    await form.trigger('submit')
    await flushPromises()

    expect(sent[0]).toEqual({
      method: 'POST',
      url: '/api/v1/matches/m1/events',
      body: { team_id: 't1', player_id: 'p1', stat: 'aces', value: 1 },
    })
  })

  it('adds a new player to a roster and lets a player leave', async () => {
    responses['POST /api/v1/competitions/league/teams/t1/roster'] = anna
    responses['POST /api/v1/roster-entries/e1/leave'] = anna
    const { page } = await open('/admin/competitions/league/teams/t1')

    await page.find('input[type="date"]').setValue('2026-12-01')
    await page.find('form.inline').trigger('submit')
    const form = page.find('form.form')
    const [first, last] = form.findAll('input:not([type])')
    await first!.setValue('Ewa')
    await last!.setValue('Lis')
    await form.find('input[type="number"]').setValue(9)
    await form.trigger('submit')
    await flushPromises()

    expect(sent).toEqual([
      { method: 'POST', url: '/api/v1/roster-entries/e1/leave', body: { left_on: '2026-12-01' } },
      {
        method: 'POST',
        url: '/api/v1/competitions/league/teams/t1/roster',
        body: {
          player: { first_name: 'Ewa', last_name: 'Lis' },
          number: 9,
          position: null,
          joined_on: null,
        },
      },
    ])
  })
})
