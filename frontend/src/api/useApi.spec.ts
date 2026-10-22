import { flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { useApi } from './useApi'

afterEach(() => vi.unstubAllGlobals())

it('drops the previous resource when the path changes, but keeps it on reload', async () => {
  let release = () => {}
  vi.stubGlobal(
    'fetch',
    vi.fn(
      (url: string) =>
        new Promise<Response>((resolve) => {
          release = () => resolve(new Response(JSON.stringify(url)))
        }),
    ),
  )
  const id = ref('m1')
  const match = useApi<string>(() => `matches/${id.value}`)
  release()
  await flushPromises()
  expect(match.data.value).toBe('/api/v1/matches/m1')

  match.reload()
  await flushPromises()
  expect(match.data.value).toBe('/api/v1/matches/m1') // still shown while reloading
  expect(match.loading.value).toBe(false)

  id.value = 'm2'
  await flushPromises()
  expect(match.data.value).toBeNull() // never m1's data under m2
  expect(match.loading.value).toBe(true)
  release()
  await flushPromises()
  expect(match.data.value).toBe('/api/v1/matches/m2')
})
