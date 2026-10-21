import { ref, watchEffect, type Ref } from 'vue'
import { getJson } from './client'

// Loads `path()` and reloads whenever it changes (e.g. a route parameter).
export function useApi<T>(path: () => string): {
  data: Ref<T | null>
  error: Ref<Error | null>
  loading: Ref<boolean>
} {
  const data = ref<T | null>(null) as Ref<T | null>
  const error = ref<Error | null>(null)
  const loading = ref(true)
  watchEffect(async (onCleanup) => {
    let current = true
    onCleanup(() => (current = false))
    loading.value = true
    error.value = null
    try {
      const body = await getJson<T>(path())
      if (current) data.value = body
    } catch (e) {
      if (current) error.value = e instanceof Error ? e : new Error(String(e))
    } finally {
      if (current) loading.value = false
    }
  })
  return { data, error, loading }
}
