import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiUrl, getJson, send } from './client'

afterEach(() => vi.unstubAllGlobals())

describe('apiUrl', () => {
  it('uses the live API path in development', () => {
    expect(apiUrl('competitions/league/standings', false)).toBe(
      '/api/v1/competitions/league/standings',
    )
  })

  it('uses the snapshot file next to the site when static', () => {
    expect(apiUrl('competitions/league/standings', true)).toBe(
      '/api/v1/competitions/league/standings.json',
    )
  })
})

describe('getJson', () => {
  it('raises ApiError for an error response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 404 })))

    await expect(getJson('competitions/missing')).rejects.toBeInstanceOf(ApiError)
  })
})

describe('send', () => {
  it('posts JSON to the live API', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response('{"slug": "league"}', { status: 201 }))
    vi.stubGlobal('fetch', fetch)

    expect(await send('POST', 'competitions', { slug: 'league' })).toEqual({ slug: 'league' })
    expect(fetch).toHaveBeenCalledWith('/api/v1/competitions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{"slug":"league"}',
    })
  })

  it('returns null for 204 No Content', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))

    expect(await send('DELETE', 'events/e1')).toBeNull()
  })

  it('carries the API error message', async () => {
    const conflict = new Response('{"detail": "fixtures already exist"}', { status: 409 })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(conflict))

    await expect(send('POST', 'competitions/x/fixtures', {})).rejects.toMatchObject({
      status: 409,
      message: 'fixtures already exist',
    })
  })

  it('lists invalid fields', async () => {
    const invalid = new Response(
      '{"detail": [{"loc": ["body", "name"], "msg": "String should have at least 1 character"}]}',
      { status: 422 },
    )
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(invalid))

    await expect(send('POST', 'teams', { name: '' })).rejects.toThrow(
      'name: String should have at least 1 character',
    )
  })

  it('shows an error on the whole body without a field name', async () => {
    const invalid = new Response(
      '{"detail": [{"loc": ["body"], "msg": "Value error, give team_id or team"}, {"msg": "odd"}]}',
      { status: 422 },
    )
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(invalid))

    await expect(send('POST', 'teams', {})).rejects.toThrow('Value error, give team_id or team; odd')
  })
})
