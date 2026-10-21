import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiUrl, getJson } from './client'

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
