import { ref, watch, type Ref } from 'vue'
import { getJson } from './client'

// Loads `path()` and reloads whenever it changes (e.g. a route parameter) or on `reload()`.
// An empty path waits: nothing is fetched until it depends on data that has loaded.
export function useApi<T>(path: () => string): {
  data: Ref<T | null>
  error: Ref<Error | null>
  loading: Ref<boolean>
  reload: () => void
} {
  const data = ref<T | null>(null) as Ref<T | null>
  const error = ref<Error | null>(null)
  const loading = ref(true)
  const version = ref(0)
  watch(
    [path, version],
    async ([url], [previousUrl], onCleanup) => {
      let current = true
      onCleanup(() => (current = false))
      // Another resource (e.g. a new route parameter): never show the previous one's data.
      if (url !== previousUrl) data.value = null
      if (!url) return
      loading.value = data.value === null // keep showing old data while reloading
      error.value = null
      try {
        const body = await getJson<T>(url)
        if (current) data.value = body
      } catch (e) {
        if (current) error.value = e instanceof Error ? e : new Error(String(e))
      } finally {
        if (current) loading.value = false
      }
    },
    { immediate: true },
  )
  return { data, error, loading, reload: () => version.value++ }
}
