import { afterEach, expect, it, vi } from 'vitest'

afterEach(() => vi.unstubAllEnvs())

async function routeNames() {
  vi.resetModules() // staticData is read when the client module loads
  const { routes } = await import('./router')
  return routes.map((r) => r.name)
}

it('includes the admin panel locally', async () => {
  expect(await routeNames()).toContain('admin')
})

it('leaves the admin panel out of the static Pages build', async () => {
  vi.stubEnv('VITE_STATIC_DATA', 'true')

  expect(await routeNames()).not.toContain('admin')
})
